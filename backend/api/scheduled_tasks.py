from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from core.models import (
    ScheduledTaskPayload, ScheduledTaskSummary, 
    TaskTemplate, TaskFromTemplatePayload, TaskCreatePayload
)
from db import scheduled_tasks_crud, templates_crud
from services.task_scheduler import scheduler
from services.provider_service import get_provider_status, get_available_models_by_provider
from core.providers import extract_provider_from_model
from services.template_engine import template_engine
from db.tasks_crud import create_task
from data.default_templates import get_default_templates
from core.config import get_logger
import croniter

router = APIRouter()
logger = get_logger("api_scheduled_tasks")

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
        
        return {"id": task_id, "message": "Scheduled task created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating scheduled task: {e}")
        raise HTTPException(status_code=500, detail="Error creating scheduled task")

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
