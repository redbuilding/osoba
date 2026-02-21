from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Request
from core.models import (
    ScheduledTaskPayload, ScheduledTaskSummary,
    TaskTemplate, TaskFromTemplatePayload, TaskCreatePayload,
    PromptImprovePayload, PromptImproveResponse
)
from db import scheduled_tasks_crud, templates_crud
from services.task_scheduler import scheduler
from services.provider_service import get_provider_status, get_available_models_by_provider
from core.providers import extract_provider_from_model
from services.template_engine import template_engine
from db.tasks_crud import create_task
from data.default_templates import get_default_templates
from core.config import get_logger, ENABLE_PROMPT_IMPROVER, IMPROVER_RATE_LIMIT_PER_MIN
from services.telemetry import record_event
import croniter

router = APIRouter()
logger = get_logger("api_scheduled_tasks")

# Simple in-memory rate limiter: global bucket per-process
_improver_calls: list[float] = []

# Scheduled Tasks endpoints
@router.post("/api/scheduled-tasks", response_model=dict)
async def create_scheduled_task(payload: ScheduledTaskPayload):
    try:
        # Validate schedule type and timing
        s_type = (payload.schedule.type or "recurring").lower()
        if s_type == "recurring":
            if not payload.schedule.cron_expression:
                raise HTTPException(status_code=400, detail="Missing cron_expression for recurring schedule")
            try:
                croniter.croniter(payload.schedule.cron_expression)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid cron expression: {e}")
        elif s_type == "once":
            if not payload.schedule.once_at:
                raise HTTPException(status_code=400, detail="Missing once_at for one-time schedule")
        else:
            raise HTTPException(status_code=400, detail=f"Invalid schedule type: {payload.schedule.type}")

        # Validate model selection if provided
        if payload.model_name:
            try:
                provider_id, clean = extract_provider_from_model(payload.model_name)
                status_info = await get_provider_status(provider_id)
                if provider_id != 'ollama' and not status_info.get('configured'):
                    raise HTTPException(status_code=400, detail=f"Provider '{provider_id}' not configured")
                models_by_provider = await get_available_models_by_provider()
                allowed = set(models_by_provider.get(provider_id, []))
                # Models list for non-ollama may be provider-prefixed in config; normalize
                if provider_id != 'ollama':
                    # accept both prefixed and clean
                    ok = (payload.model_name in allowed) or (clean in {m.split('/',1)[1] if '/' in m else m for m in allowed})
                else:
                    ok = clean in allowed or payload.model_name in allowed
                if not ok:
                    raise HTTPException(status_code=400, detail=f"Model '{payload.model_name}' not available for provider '{provider_id}'")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid model: {e}")
        
        # Create scheduled task
        task_data = payload.model_dump()
        task_id = await scheduler.schedule_task(task_data)
        try:
            accepted = bool((payload.planner_hints or {}).get('manifest') or (payload.planner_hints or {}).get('step_plan'))
            record_event("improver.accept", {"with_hints": accepted})
        except Exception:
            pass
        
        return {"id": task_id, "message": "Scheduled task created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating scheduled task: {e}")
        raise HTTPException(status_code=500, detail="Error creating scheduled task")


@router.post("/api/scheduled-tasks/improve-instruction", response_model=PromptImproveResponse)
async def improve_scheduled_instruction(payload: PromptImprovePayload, request: Request):
    """Improve a Scheduled Task instruction and return improved text + planner hints.

    Does not mutate any server state. Uses the selected model if provided, otherwise a sensible default.
    """
    if not ENABLE_PROMPT_IMPROVER:
        record_event("improver.disabled", {})
        raise HTTPException(status_code=404, detail="Prompt improver disabled")

    # Global rate limit (per-process). Optimistic and simple.
    try:
        import time
        now = time.time()
        window = 60.0
        # prune
        while _improver_calls and now - _improver_calls[0] > window:
            _improver_calls.pop(0)
        if len(_improver_calls) >= max(IMPROVER_RATE_LIMIT_PER_MIN, 1):
            record_event("improver.rate_limited", {"limit": IMPROVER_RATE_LIMIT_PER_MIN})
            raise HTTPException(status_code=429, detail="Too many improv requests; please retry shortly")
        _improver_calls.append(now)
    except HTTPException:
        raise
    except Exception:
        pass
    # Validate mode
    mode = (payload.mode or "Clarify").strip().lower()
    mode = mode if mode in {"clarify", "expand", "tighten", "translate"} else "clarify"

    # Resolve/validate model if provided
    model_name = payload.model_name
    if model_name:
        try:
            provider_id, clean = extract_provider_from_model(model_name)
            status_info = await get_provider_status(provider_id)
            if provider_id != 'ollama' and not status_info.get('configured'):
                raise HTTPException(status_code=400, detail=f"Provider '{provider_id}' not configured")
            models_by_provider = await get_available_models_by_provider()
            allowed = set(models_by_provider.get(provider_id, []))
            if provider_id != 'ollama':
                ok = (model_name in allowed) or (clean in {m.split('/',1)[1] if '/' in m else m for m in allowed})
            else:
                ok = clean in allowed or model_name in allowed
            if not ok:
                raise HTTPException(status_code=400, detail=f"Model '{model_name}' not available for provider '{provider_id}'")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid model: {e}")

    # Build improvement prompt
    objectives = {
        "clarify": "Clarify and disambiguate without changing intent.",
        "expand": "Expand with necessary specifics, inputs/outputs, acceptance criteria.",
        "tighten": "Tighten and simplify; remove redundancy while keeping details needed to execute.",
        "translate": f"Translate to {payload.language or 'English'} while preserving structure and intent.",
    }
    mode_line = objectives.get(mode, objectives["clarify"])

    # Planner-aware output contract
    json_contract = {
        "type": "object",
        "required": ["improved_text", "manifest", "step_plan"],
        "properties": {
            "improved_text": {"type": "string"},
            "manifest": {"type": "object"},
            "step_plan": {"type": "array"},
            "warnings": {"type": "array", "items": {"type": "string"}}
        }
    }

    system = (
        "You are a task instruction improver for an orchestrated, multi-step planner.\n"
        "Output strict JSON only, no prose.\n"
        "Goals: preserve user intent, remove ambiguity, and produce a compact contracts manifest.\n"
        "The manifest lists stable identifiers (files, selectors, sections, routes, schema keys) and rules that later steps must follow.\n"
        "For the step_plan, propose 3–8 steps aligned to our toolset (llm.generate, web_search, python.*, codex.run), referencing manifest keys.\n"
        "Do not invent identifiers that aren't in the manifest; if necessary, add them explicitly to the manifest and reference them consistently.\n"
    )
    user = (
        f"Task type: {payload.task_type or 'scheduled'}\n"
        f"Mode: {mode}\n"
        f"Instruction (draft):\n{payload.draft_text}\n\n"
        f"Context hints (optional, free-form):\n{(payload.context_hints or {})}\n\n"
        "Constraints:\n"
        "- Keep identifiers stable; list them under manifest.identifiers with clear categories.\n"
        "- Specify outputs and acceptance criteria.\n"
        "- If HTML/CSS is implied, align classes/IDs; if ToC/report is implied, ensure sections match.\n"
        "- Avoid provider-specific tokens or secrets.\n"
        f"JSON schema (guidance): {__import__('json').dumps(json_contract)}\n"
        "Return only JSON with keys: improved_text, manifest, step_plan, warnings?\n"
    )

    # Choose model: provided or default
    try:
        from services.llm_service import get_default_ollama_model
        resolved_model = model_name or await get_default_ollama_model()
    except Exception:
        resolved_model = model_name or "llama3.1"

    try:
        from services.provider_service import chat_with_provider
        record_event("improver.request", {"mode": mode, "model": resolved_model})
        raw = await chat_with_provider([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], resolved_model)
        data = raw and __import__('json').loads(raw)
        if not data or not isinstance(data, dict):
            raise RuntimeError("Model did not return JSON object")
        # Minimal normalization
        resp = PromptImproveResponse(
            improved_text=str(data.get("improved_text") or payload.draft_text),
            manifest=data.get("manifest") or {},
            step_plan=data.get("step_plan") or [],
            warnings=data.get("warnings") or None,
        )
        try:
            manifest_size = len(resp.manifest or {})
            step_count = len(resp.step_plan or [])
            record_event("improver.success", {
                "mode": mode,
                "model": resolved_model,
                "manifest_keys": manifest_size,
                "steps": step_count,
                "draft_len": len(payload.draft_text or ""),
                "improved_len": len(resp.improved_text or ""),
            })
        except Exception:
            pass
        return resp
    except HTTPException:
        raise
    except Exception as e:
        # Do not log full draft; only the error message
        logger.error(f"Improver call failed: {e.__class__.__name__}: {e}")
        record_event("improver.failure", {"mode": mode, "error": type(e).__name__})
        # Be optimistic: return the draft with empty hints
        return PromptImproveResponse(
            improved_text=payload.draft_text,
            manifest={},
            step_plan=[],
            warnings=[f"Improver failed: {e}"]
        )

@router.post("/api/scheduled-tasks/{task_id}/run", response_model=dict)
async def run_scheduled_task_now(task_id: str, payload: dict | None = None):
    """Immediately create a Task from a scheduled task, optionally overriding model_name."""
    try:
        scheduled = scheduled_tasks_crud.get_scheduled_task(task_id)
        if not scheduled:
            raise HTTPException(status_code=404, detail="Scheduled task not found")

        override_model = None
        if payload and isinstance(payload, dict):
            override_model = payload.get("model_name")
        # Validate override if present
        if override_model:
            provider_id, clean = extract_provider_from_model(override_model)
            status_info = await get_provider_status(provider_id)
            if provider_id != 'ollama' and not status_info.get('configured'):
                raise HTTPException(status_code=400, detail=f"Provider '{provider_id}' not configured")
            models_by_provider = await get_available_models_by_provider()
            allowed = set(models_by_provider.get(provider_id, []))
            if provider_id != 'ollama':
                ok = (override_model in allowed) or (clean in {m.split('/',1)[1] if '/' in m else m for m in allowed})
            else:
                ok = clean in allowed or override_model in allowed
            if not ok:
                raise HTTPException(status_code=400, detail=f"Model '{override_model}' not available for provider '{provider_id}'")

        task_data = {
            "goal": scheduled["goal"],
            "title": scheduled.get("name", scheduled["goal"][:50]),
            "conversation_id": scheduled.get("conversation_id"),
            "model_name": override_model or scheduled.get("model_name") or scheduled.get("ollama_model_name"),
            "budget": scheduled.get("budget"),
            "status": "PLANNING",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "priority": 1,
        }
        new_task_id = create_task(task_data)
        return {"task_id": new_task_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running scheduled task now: {e}")
        raise HTTPException(status_code=500, detail="Error running scheduled task")

@router.get("/api/scheduled-tasks")
async def list_scheduled_tasks():
    try:
        tasks = scheduled_tasks_crud.list_scheduled_tasks()
        result = []
        for task in tasks:
            # Manually set id field from _id
            task_dict = dict(task)
            task_dict['id'] = str(task_dict.pop('_id'))  # Remove _id and set id
            # Flatten next_run and last_run for convenience
            sched = task_dict.get('schedule') or {}
            if 'next_run' in sched:
                task_dict['next_run'] = sched.get('next_run')
            if 'timezone' in sched:
                task_dict['timezone'] = sched.get('timezone')
            # Add delay info if available
            if 'last_delay_minutes' in task_dict:
                task_dict['last_delay_minutes'] = task_dict.get('last_delay_minutes', 0)
            result.append(task_dict)
        return result
    except Exception as e:
        logger.error(f"Error listing scheduled tasks: {e}")
        raise HTTPException(status_code=500, detail="Error listing scheduled tasks")

@router.delete("/api/scheduled-tasks/{task_id}")
async def delete_scheduled_task(task_id: str):
    try:
        success = scheduled_tasks_crud.delete_scheduled_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Scheduled task not found")
        
        # Remove from scheduler
        if task_id in scheduler.scheduled_tasks:
            del scheduler.scheduled_tasks[task_id]
        
        return {"message": "Scheduled task deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting scheduled task: {e}")
        raise HTTPException(status_code=500, detail="Error deleting scheduled task")

# Templates endpoints
@router.get("/api/templates")
async def list_templates(category: str = None):
    try:
        templates = templates_crud.list_templates(category=category)
        result = []
        for tmpl in templates:
            # Manually set id field from _id
            tmpl_dict = dict(tmpl)
            tmpl_dict['id'] = str(tmpl_dict.pop('_id'))  # Remove _id and set id
            result.append(tmpl_dict)
        return result
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail="Error listing templates")

@router.get("/api/templates/default", response_model=List[dict])
async def get_default_templates_endpoint():
    """Get default templates for initialization."""
    return get_default_templates()

@router.post("/api/templates", response_model=dict)
async def create_template(template: TaskTemplate):
    try:
        template_data = template.model_dump(exclude={"id"})
        template_id = templates_crud.create_template(template_data)
        return {"id": template_id, "message": "Template created successfully"}
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail="Error creating template")

@router.post("/api/templates/{template_id}/create-task", response_model=dict)
async def create_task_from_template(template_id: str, payload: TaskFromTemplatePayload):
    try:
        # Get template
        template_doc = templates_crud.get_template(template_id)
        if not template_doc:
            raise HTTPException(status_code=404, detail="Template not found")
        
        template = TaskTemplate.model_validate({**template_doc, "_id": str(template_doc["_id"])})
        
        # Validate parameters
        missing_params = template_engine.validate_parameters(template, payload.parameters)
        if missing_params:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required parameters: {', '.join(missing_params)}"
            )
        
        # Render template
        rendered_goal = template_engine.render_template(template, payload.parameters)
        
        # Create task
        task_data = {
            "goal": rendered_goal,
            "conversation_id": payload.conversation_id,
            "model_name": payload.model_name,
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        task_id = create_task(task_data)
        return {"task_id": task_id, "rendered_goal": rendered_goal}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task from template: {e}")
        raise HTTPException(status_code=500, detail="Error creating task from template")

@router.get("/api/templates/{template_id}/parameters", response_model=List[str])
async def get_template_parameters(template_id: str):
    try:
        template_doc = templates_crud.get_template(template_id)
        if not template_doc:
            raise HTTPException(status_code=404, detail="Template not found")
        
        template = TaskTemplate.model_validate({**template_doc, "_id": str(template_doc["_id"])})
        parameters = template_engine.get_template_parameters(template.goal_template)
        
        return parameters
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template parameters: {e}")
        raise HTTPException(status_code=500, detail="Error getting template parameters")
