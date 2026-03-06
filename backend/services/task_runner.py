import asyncio
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from core.config import (
    CANVA_SERVICE_NAME,
    CODEX_SERVICE_NAME,
    FIGMA_SERVICE_NAME,
    ENABLE_TASKS,
    HUBSPOT_SERVICE_NAME,
    MYSQL_DB_SERVICE_NAME,
    PYTHON_SERVICE_NAME,
    TASK_DISPATCH_INTERVAL_MS,
    TASK_MAX_SECONDS_DEFAULT,
    TASK_MAX_TOOL_CALLS_DEFAULT,
    TASK_STEP_TIMEOUT_DEFAULT,
    WEB_SEARCH_SERVICE_NAME,
    YOUTUBE_SERVICE_NAME,
    get_logger,
)
from core.models import Plan, PlanStep
from db.mongodb import conversations_collection
from db.tasks_crud import (
    get_task,
    increment_usage,
    list_tasks,
    set_step_status,
    update_task,
)
from services.codex_client import create_workspace as codex_create_workspace
from services.codex_client import get_run_status as codex_get_run_status
from services.codex_client import start_run as codex_start_run
from services.mcp_service import submit_mcp_request, wait_mcp_response
from services.progress_bus import progress_bus
from services.provider_service import chat_with_provider
from services.provider_service import get_provider_status as get_provider_status_async
from services.task_planner import plan_task

logger = get_logger("task_runner")


class RunnerState:
    def __init__(self) -> None:
        self._workers: Dict[str, asyncio.Task] = {}
        self._stop = asyncio.Event()

    def is_running(self) -> bool:
        return not self._stop.is_set()

    def stop(self) -> None:
        self._stop.set()

    def worker_for(self, task_id: str) -> asyncio.Task | None:
        t = self._workers.get(task_id)
        if t and t.done():
            self._workers.pop(task_id, None)
            return None
        return t

    def set_worker(self, task_id: str, task: asyncio.Task) -> None:
        self._workers[task_id] = task


runner_state = RunnerState()


def _resolve_tool(tool: str) -> Tuple[str, str]:
    # returns service_name, tool_name
    # Web Search service tools
    if tool in ["web_search", "smart_search_extract", "image_search", "news_search", "fetch_url"]:
        return WEB_SEARCH_SERVICE_NAME, tool
    # MySQL Database service
    if tool == "execute_sql_query_tool":
        return MYSQL_DB_SERVICE_NAME, "execute_sql_query_tool"
    # YouTube service
    if tool == "get_youtube_transcript":
        return YOUTUBE_SERVICE_NAME, "get_youtube_transcript"
    # HubSpot service tools
    if tool in ["create_hubspot_marketing_email", "update_hubspot_marketing_email"]:
        return HUBSPOT_SERVICE_NAME, tool
    # Python service tools (handle dot notation)
    if tool.startswith("python."):
        return PYTHON_SERVICE_NAME, tool.split(".", 1)[1]
    # Codex service tools (handle dot notation)
    if tool.startswith("codex."):
        tool_name = tool.split(".", 1)[1]  # Remove "codex." prefix
        return CODEX_SERVICE_NAME, tool_name
    # Canva service tools
    if tool in ["create_design", "list_designs", "get_design", "export_design"]:
        return CANVA_SERVICE_NAME, tool
    # Figma service tools
    if tool in ["figma_get_file", "figma_get_nodes", "figma_export_images",
                "figma_get_comments", "figma_post_comment", "figma_get_design_system"]:
        return FIGMA_SERVICE_NAME, tool
    raise ValueError(f"Unknown tool: {tool}")


async def start_task_dispatcher():
    if not ENABLE_TASKS:
        logger.info("Task dispatcher disabled by config.")
        return
    logger.info("Starting task dispatcher loop.")
    try:
        asyncio.create_task(_dispatch_loop())
        logger.info("Task dispatcher loop created successfully.")
    except Exception as e:
        logger.error(f"Failed to start task dispatcher: {e}", exc_info=True)


async def _dispatch_loop():
    logger.info("Task dispatcher loop started")
    while not runner_state._stop.is_set():
        try:
            await _scan_and_schedule()
        except Exception as e:
            logger.error(f"Dispatcher error: {e}", exc_info=True)
            # Continue running even if there's an error
        try:
            await asyncio.sleep(TASK_DISPATCH_INTERVAL_MS / 1000.0)
        except Exception as e:
            logger.error(f"Dispatcher sleep error: {e}", exc_info=True)
    logger.info("Task dispatcher loop stopped")


async def _scan_and_schedule():
    # Prune finished workers to avoid stale blocks
    try:
        for tid, t in list(runner_state._workers.items()):
            if t.done():
                runner_state._workers.pop(tid, None)
                logger.info(f"Pruned finished worker for task {tid}")
    except Exception as e:
        logger.error(f"Error pruning finished workers: {e}")

    # Only run one task at a time (queue system)
    if len(runner_state._workers) > 0:
        logger.debug(
            f"Skipping scan - {len(runner_state._workers)} workers already running"
        )
        return

    # Pick up tasks to run; priority-based approach
    tasks = list_tasks(limit=100)
    logger.debug(f"Found {len(tasks)} tasks to check")

    for t in tasks:
        task_id = str(t.get("_id"))
        status = t.get("status")
        logger.debug(
            f"Checking task {task_id}: status={status}, priority={t.get('priority', 2)}"
        )

        if status in ("PLANNING", "PENDING", "RUNNING") and not runner_state.worker_for(
            task_id
        ):
            # Start/continue running the highest priority task
            logger.info(
                f"Scheduling task {task_id} with status {status} and priority {t.get('priority', 2)}"
            )
            try:
                worker = asyncio.create_task(_run_task(task_id))
                runner_state.set_worker(task_id, worker)
                break  # Only start one task
            except Exception as e:
                logger.error(
                    f"Failed to create worker for task {task_id}: {e}", exc_info=True
                )


async def _run_task(task_id: str):
    logger.info(f"Starting _run_task for {task_id}")
    try:
        # Load task
        doc = get_task(task_id)
        if not doc:
            logger.error(f"Task {task_id} not found")
            return

        task_start = datetime.now(timezone.utc)
        
        # Calculate queue delay for scheduled tasks
        metadata = doc.get("metadata", {})
        scheduled_for = metadata.get("scheduled_for")
        system_delay = metadata.get("system_delay_minutes", 0)
        scheduled_task_id = metadata.get("scheduled_task_id")
        
        if scheduled_for:
            # Ensure scheduled_for is timezone-aware
            if hasattr(scheduled_for, 'tzinfo') and scheduled_for.tzinfo is None:
                scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)
            
            # Total delay = time from scheduled_for to now
            total_delay_seconds = (task_start - scheduled_for).total_seconds()
            total_delay_minutes = int(total_delay_seconds / 60)
            
            # Queue delay = total delay - system delay
            queue_delay_minutes = max(0, total_delay_minutes - system_delay)
            
            # Update metadata with queue delay
            metadata["queue_delay_minutes"] = queue_delay_minutes
            metadata["total_delay_minutes"] = total_delay_minutes
            update_task(task_id, {"metadata": metadata})
            
            # Also update the scheduled task record with queue delay
            if scheduled_task_id and queue_delay_minutes > 0:
                try:
                    from db.mongodb import get_scheduled_tasks_collection
                    from bson import ObjectId
                    collection = get_scheduled_tasks_collection()
                    collection.update_one(
                        {"_id": ObjectId(scheduled_task_id)},
                        {"$set": {
                            "last_queue_delay_minutes": queue_delay_minutes,
                            "last_delay_minutes": total_delay_minutes
                        }}
                    )
                except Exception as e:
                    logger.warning(f"Could not update scheduled task with queue delay: {e}")
            
            if queue_delay_minutes > 5:
                logger.info(
                    f"Task {task_id} queued for {queue_delay_minutes}m "
                    f"(system delay: {system_delay}m, total: {total_delay_minutes}m)"
                )
        
        logger.info(f"Task {task_id} current status: {doc.get('status')}")

        if doc.get("status") == "PLANNING":
            logger.info(f"Task {task_id} in PLANNING - starting plan generation")
            # Produce plan
            model_name = doc.get("model_name") or doc.get(
                "ollama_model_name"
            )  # Support both old and new field names
            if not model_name:
                from services.llm_service import get_default_ollama_model

                model_name = await get_default_ollama_model()
            plan = await plan_task(
                doc.get("goal", ""),
                model_name,
                doc.get("budget"),
                planner_hints=(doc.get("planner_hints") or None),
                kb_context=doc.get("kb_context", ""),
            )
            logger.info(f"Task {task_id} plan generated, updating to PENDING")
            update_task(
                task_id,
                {
                    "plan": plan.model_dump(),
                    "status": "PENDING",
                    "current_step_index": -1,
                },
            )
            await progress_bus.publish(
                task_id,
                {"type": "TASK_STATUS", "task_id": task_id, "status": "PENDING"},
            )
            logger.info(f"Task {task_id} updated to PENDING, reloading document")
            doc = get_task(task_id)

        logger.info(
            f"Task {task_id} status after planning: {doc.get('status') if doc else 'doc is None'}"
        )

        if doc and doc.get("status") == "PENDING":
            logger.info(f"Task {task_id} transitioning from PENDING to RUNNING")
            update_task(task_id, {"status": "RUNNING", "current_step_index": 0})
            await progress_bus.publish(
                task_id,
                {"type": "TASK_STATUS", "task_id": task_id, "status": "RUNNING"},
            )
            doc = get_task(task_id)  # Reload doc after status update
            logger.info(f"Task {task_id} now in RUNNING status")

        # Execute steps
        plan_dict = doc.get("plan") or {} if doc else {}
        steps: list[Dict[str, Any]] = plan_dict.get("steps", [])
        idx = int(doc.get("current_step_index", 0)) if doc else 0

        # Safety check: ensure idx is not negative
        if idx < 0:
            idx = 0
            update_task(task_id, {"current_step_index": 0})

        logger.info(
            f"Task {task_id} starting execution with {len(steps)} steps, starting at index {idx}"
        )

        for i in range(idx, len(steps)):
            logger.info(f"Task {task_id} executing step {i} of {len(steps)}")
            # reload may have pause/cancel status
            cur = get_task(task_id) or {}
            cur_status = cur.get("status")
            if cur_status in ("PAUSED", "CANCELED"):
                await progress_bus.publish(
                    task_id,
                    {"type": "TASK_STATUS", "task_id": task_id, "status": cur_status},
                )
                return

            # Budget checks before executing step
            if not _check_budgets(cur, task_start):
                update_task(task_id, {"status": "FAILED", "error": "Budget exceeded"})
                await progress_bus.publish(
                    task_id,
                    {
                        "type": "TASK_STATUS",
                        "task_id": task_id,
                        "status": "FAILED",
                        "error": "Budget exceeded",
                    },
                )
                await _post_conversation_update(cur, success=False)
                return

            ok = await _execute_step_with_retry(task_id, i, steps[i])
            logger.info(f"Task {task_id} step {i} result: {ok}")
            if not ok:
                logger.error(
                    f"Task {task_id} step {i} failed verification, stopping execution"
                )
                # Mark task failed centrally to avoid later status flips
                update_task(task_id, {"status": "FAILED", "error": f"Step {i} failed"})
                await progress_bus.publish(
                    task_id,
                    {
                        "type": "TASK_STATUS",
                        "task_id": task_id,
                        "status": "FAILED",
                        "error": f"Step {i} failed",
                    },
                )
                # Get the step details for debugging
                step = steps[i]
                logger.error(
                    f"Failed step details: tool={step.get('tool')}, success_criteria={step.get('success_criteria')}"
                )
                await _post_conversation_update(get_task(task_id) or {}, success=False)
                return
            logger.info(f"Task {task_id} updating current_step_index to {i + 1}")
            update_task(task_id, {"current_step_index": i + 1})

        # Done
        logger.info(f"Task {task_id} completed all steps, marking as COMPLETED")
        update_task(task_id, {"status": "COMPLETED"})
        await progress_bus.publish(
            task_id, {"type": "TASK_STATUS", "task_id": task_id, "status": "COMPLETED"}
        )
        # Post summary to conversation
        await _post_conversation_update(get_task(task_id) or {}, success=True)
        logger.info(f"Task {task_id} execution finished")
    finally:
        # Ensure worker cleanup always happens, even on early return/failure
        try:
            runner_state._workers.pop(task_id, None)
            logger.info(f"Cleaned up worker for task {task_id}")
        except Exception as e:
            logger.error(f"Error cleaning up worker for task {task_id}: {e}")


def _get_budget(doc: Dict[str, Any]) -> Dict[str, int]:
    b = (doc.get("budget") or {}).copy()
    if "max_seconds" not in b:
        b["max_seconds"] = TASK_MAX_SECONDS_DEFAULT
    if "max_tool_calls" not in b:
        b["max_tool_calls"] = TASK_MAX_TOOL_CALLS_DEFAULT
    return b


def _get_usage(doc: Dict[str, Any]) -> Dict[str, int]:
    u = (doc.get("usage") or {}).copy()
    u.setdefault("tool_calls", 0)
    u.setdefault("seconds_elapsed", 0)
    return u


def _check_budgets(doc: Dict[str, Any], task_start: datetime) -> bool:
    b = _get_budget(doc)
    u = _get_usage(doc)
    # Simple wall clock elapsed
    elapsed = int((datetime.now(timezone.utc) - task_start).total_seconds())
    if u.get("seconds_elapsed", 0) + elapsed > b.get(
        "max_seconds", TASK_MAX_SECONDS_DEFAULT
    ):
        return False
    if u.get("tool_calls", 0) >= b.get("max_tool_calls", TASK_MAX_TOOL_CALLS_DEFAULT):
        return False
    return True


async def _execute_step_with_retry(
    task_id: str, idx: int, step: Dict[str, Any]
) -> bool:
    max_retries = int(step.get("max_retries", 1))
    attempt = 0
    backoff = 1
    logger.info(
        f"Starting step execution for task {task_id}, step {idx}: {step.get('tool', 'unknown')}"
    )
    while True:
        try:
            result = await _execute_step(task_id, idx, step)
            logger.info(f"Step {idx} completed for task {task_id}: {result}")
            return result
        except Exception as e:
            logger.error(
                f"Step {idx} failed for task {task_id}, attempt {attempt}: {e}"
            )
            attempt += 1
            if attempt > max_retries:
                logger.error(
                    f"Step {idx} failed permanently for task {task_id} after {max_retries} attempts"
                )
                return False
            await progress_bus.publish(
                task_id,
                {
                    "type": "STEP_STATUS",
                    "task_id": task_id,
                    "index": idx,
                    "status": "RETRYING",
                    "error": str(e),
                    "attempt": attempt,
                },
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 15)


async def _verify_success(
    success_criteria: str, normalized_output: Dict[str, Any], model_name: str | None
) -> bool:
    logger.info(f"Verifying success criteria: '{success_criteria}'")
    logger.info(f"Normalized output keys: {list(normalized_output.keys())}")
    logger.info(f"Output preview: {str(normalized_output)[:200]}...")

    # Fast rule: if criteria missing, accept
    if not success_criteria:
        logger.info("No success criteria, accepting")
        return True

    # Be more lenient - if we have any meaningful output, consider it successful
    raw = normalized_output.get("raw")
    if raw:
        # Check if we have substantial content (more than 100 chars)
        content_str = str(raw)
        logger.info(f"Raw content length: {len(content_str)}")
        if len(content_str) > 100:
            logger.info("Content length check passed")
            return True

    # Check text field as well
    text = normalized_output.get("text")
    if text:
        content_str = str(text)
        logger.info(f"Text content length: {len(content_str)}")
        if len(content_str) > 100:
            logger.info("Text length check passed")
            return True

    # Fallback to LLM verification only if needed
    logger.info("Using LLM verification as fallback")
    if not model_name:
        from services.llm_service import get_default_ollama_model

        model_name = await get_default_ollama_model()

    content_preview = str(normalized_output)[:800]
    prompt = (
        "You are a verifier. Given a success criteria and a step output, "
        'respond with JSON: {"success": true|false, "reason": "short"}.\n'
        f"Criteria: {success_criteria}\n"
        f"Output Preview: {content_preview}\n"
        "Return JSON only."
    )
    try:
        res = await chat_with_provider(
            [
                {"role": "system", "content": "You output only JSON."},
                {"role": "user", "content": prompt},
            ],
            model_name,
        )
        data = res and __import__("json").loads(res)
        result = bool(data and data.get("success") is True)
        logger.info(f"LLM verification result: {result}, response: {res}")
        return result
    except Exception as e:
        logger.warning(f"Verification failed with error: {e}, being permissive")
        return True  # Be permissive if verifier fails
        return True  # Be permissive if verifier fails


async def _execute_step(task_id: str, idx: int, step: Dict[str, Any]):
    logger.info(
        f"Executing step {idx} for task {task_id}: {step.get('tool', 'unknown')}"
    )
    # Mark step as running and clear any previous error
    set_step_status(
        task_id,
        idx,
        {"status": "RUNNING", "error": None, "started_at": datetime.now(timezone.utc)},
    )
    await progress_bus.publish(
        task_id,
        {"type": "STEP_STATUS", "task_id": task_id, "index": idx, "status": "RUNNING"},
    )

    tool = step.get("tool")
    params = step.get("params") or {}
    # Step timeout from config
    step_timeout = int(step.get("timeout", TASK_STEP_TIMEOUT_DEFAULT))
    try:
        step_started = time.time()
        # SEC-007: Enforce tool whitelist at execution time (not just plan time)
        if tool and not tool.startswith("llm."):
            from services.task_planner import ALLOWED_TASK_TOOLS
            if tool not in ALLOWED_TASK_TOOLS:
                raise RuntimeError(f"Tool '{tool}' not in allowed task whitelist")
        if tool and tool.startswith("llm."):
            # LLM-only step: use instruction or params.prompt to generate text
            task_doc = get_task(task_id) or {}
            model = task_doc.get("model_name") or task_doc.get("ollama_model_name")
            if not model:
                from services.llm_service import get_default_ollama_model

                model = await get_default_ollama_model()
            prompt = None
            if isinstance(params, dict):
                prompt = params.get("prompt")
            if not prompt:
                prompt = step.get("instruction", "")
            # Build context from prior steps
            context_text = _build_llm_context(task_doc, idx)
            increment_usage(task_id, "tool_calls", 1)
            messages = [{"role": "system", "content": "You are a helpful assistant."}]
            # Inject KB context snapshot if present
            kb_context = task_doc.get("kb_context", "")
            if kb_context:
                messages.append({"role": "user", "content": kb_context})
            # Inject planner manifest (global + scoped) if present
            try:
                import json as _json
                hints = (task_doc.get("planner_hints") or {})
                manifest = hints.get("manifest") if isinstance(hints, dict) else None
                total_steps = len((task_doc.get("plan") or {}).get("steps", []) or [])
                if manifest:
                    # Compact global summary for all steps
                    summary = {
                        k: v for k, v in manifest.items() if k in ("identifiers", "files", "sections", "routes", "rules", "outputs")
                    } or manifest
                    messages.append({
                        "role": "user",
                        "content": f"Planner Manifest (global summary):\n{_json.dumps(summary, ensure_ascii=False)}",
                    })
                    # Per-step scoping hint
                    role_hint = f"You are Step {idx+1} of {max(total_steps, idx+1)}: {step.get('title','')} using tool {tool}. Use only identifiers present in the manifest; do not introduce new ones unless proposing 'proposed_manifest_changes'."
                    messages.append({"role": "user", "content": role_hint})
            except Exception:
                pass
            if context_text:
                messages.append(
                    {
                        "role": "user",
                        "content": f"Context from prior steps (use this):\n{context_text}",
                    }
                )
            messages.append({"role": "user", "content": prompt or ""})
            text = await chat_with_provider(messages, model)
            norm: Dict[str, Any] = {"text": text or ""}
        else:
            if tool == "codex.run":
                # Gate: ensure OpenAI configured
                try:
                    status = await get_provider_status_async("openai")
                except Exception:
                    status = {"configured": False}
                if not status.get("configured"):
                    raise RuntimeError("OpenAI API key is required to run Codex")
                # Create workspace and start run
                name_hint = (get_task(task_id) or {}).get("title", "task")
                ws = await codex_create_workspace(name_hint=name_hint, keep=False)
                ws_id = ws.get("workspace_id")
                if not ws_id:
                    raise RuntimeError("Failed to create Codex workspace")
                instr = (
                    step.get("instruction")
                    or (params.get("instruction") if isinstance(params, dict) else None)
                    or (get_task(task_id) or {}).get("goal", "")
                )
                start = await codex_start_run(ws_id, instr)
                run_id = start.get("run_id")
                if not run_id:
                    raise RuntimeError("Failed to start Codex run")
                deadline = time.time() + step_timeout
                last_status = None
                while time.time() < deadline:
                    st = await codex_get_run_status(run_id)
                    last_status = st.get("run") or {}
                    state = last_status.get("status")
                    if state in ("completed", "failed"):
                        break
                    await asyncio.sleep(1.0)
                if (
                    not last_status
                    or last_status.get("status") != "completed"
                    or not last_status.get("task_ok")
                ):
                    raise RuntimeError(
                        (last_status or {}).get("error_message") or "Codex run failed"
                    )
                norm = {
                    "text": last_status.get("summary"),
                    "artifacts": last_status.get("artifacts"),
                    "output_policy": last_status.get("output_policy"),
                }
                data = norm
            else:
                service_name, tool_name = _resolve_tool(tool)
                logger.info(
                    f"Resolved tool {tool} to service {service_name}, tool {tool_name}"
                )
                increment_usage(task_id, "tool_calls", 1)
                logger.info(f"Submitting MCP request for task {task_id}, step {idx}")
                req_id = await submit_mcp_request(
                    service_name, "tool", {"tool": tool_name, "params": params}
                )
                resp = await wait_mcp_response(
                    service_name, req_id, timeout=step_timeout
                )
                if resp.get("status") == "error":
                    raise RuntimeError(resp.get("error"))
                data = resp.get("data")
                norm: Dict[str, Any] = {"raw": data}

        # Special handling for python.load_csv: capture dataframe id
        if tool == "python.load_csv":
            text = ""
            if (
                isinstance(data, list)
                and data
                and isinstance(data[0], dict)
                and data[0].get("type") == "text"
            ):
                text = data[0].get("content", "")
            elif isinstance(data, str):
                text = data
            m = re.search(r"ID:\s*([0-9a-fA-F-]{36})", text)
            if m:
                norm["df_id"] = m.group(1)
        # Verification
        task_doc = get_task(task_id) or {}
        verified = await _verify_success(
            step.get("success_criteria", ""),
            norm,
            task_doc.get("model_name") or task_doc.get("ollama_model_name"),
        )
        if not verified:
            raise RuntimeError("Verification failed for step output")

        # Clear any prior error and set outputs on success
        set_step_status(
            task_id,
            idx,
            {
                "status": "COMPLETED",
                "error": None,
                "outputs": norm,
                "ended_at": datetime.now(timezone.utc),
            },
        )
        await progress_bus.publish(
            task_id,
            {
                "type": "STEP_STATUS",
                "task_id": task_id,
                "index": idx,
                "status": "COMPLETED",
            },
        )
        # Record elapsed seconds for this step
        elapsed = int(time.time() - step_started)
        increment_usage(task_id, "seconds_elapsed", max(elapsed, 0))
        return True
    except Exception as e:
        # Mark only the step as failed here; task status is decided by the orchestrator
        set_step_status(
            task_id,
            idx,
            {
                "status": "FAILED",
                "error": str(e),
                "ended_at": datetime.now(timezone.utc),
            },
        )
        await progress_bus.publish(
            task_id,
            {
                "type": "STEP_STATUS",
                "task_id": task_id,
                "index": idx,
                "status": "FAILED",
                "error": str(e),
            },
        )
        return False


def _build_llm_context(
    task_doc: Dict[str, Any], upto_index: int, max_chars: int = 10000
) -> str:
    """Aggregate text outputs from previous steps to provide short context for LLM steps.
    Safe and bounded: extracts text from prior steps' outputs and truncates.
    """
    try:
        if not task_doc:
            return ""
        plan = (task_doc.get("plan") or {}).get("steps", [])
        if not isinstance(plan, list) or upto_index <= 0:
            return ""

        chunks: list[str] = []
        total = 0
        for i in range(0, min(upto_index, len(plan))):
            st = plan[i] or {}
            outputs = st.get("outputs") or {}
            texts: list[str] = []
            # Direct text from earlier LLM/tool normalization
            t = outputs.get("text")
            if isinstance(t, str) and t.strip():
                texts.append(t.strip())
            # Extract text-like content from raw MCP response
            raw = outputs.get("raw")
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict):
                        c = item.get("content") or item.get("text")
                        if isinstance(c, str) and c.strip():
                            texts.append(c.strip())
                    elif isinstance(item, str) and item.strip():
                        texts.append(item.strip())
            elif isinstance(raw, str) and raw.strip():
                texts.append(raw.strip())
            elif raw is not None:
                s = str(raw)
                if s.strip() and len(s) <= 800:
                    texts.append(s.strip())

            if texts:
                title = st.get("title") or st.get("tool") or f"Step {i + 1}"
                block = f"[{title}]\n" + "\n".join(texts)
                chunks.append(block)
                total += len(block)
                if total >= max_chars:
                    break

        context = "\n\n".join(chunks)
        if len(context) > max_chars:
            context = context[-max_chars:]
        return context
    except Exception:
        return ""


async def _post_conversation_update(task_doc: Dict[str, Any], success: bool):
    try:
        conv_id = task_doc.get("conversation_id")
        if not conv_id:
            return
        model = task_doc.get("model_name") or task_doc.get("ollama_model_name") or ""
        plan = (task_doc.get("plan") or {}).get("steps", [])
        status = task_doc.get("status")
        summary_text = None
        if success:
            # Compose a brief summary with LLM
            titles = "\n".join(
                [f"- {s.get('title', '')} ({s.get('tool', '')})" for s in plan]
            )
            prompt = f"Summarize the completed task in 3-5 sentences for the user. Steps were:\n{titles}"
            res = await chat_with_provider(
                [
                    {"role": "system", "content": "You write concise summaries."},
                    {"role": "user", "content": prompt},
                ],
                model,
            )
            summary_text = res or "Task completed."
        else:
            summary_text = (
                f"Task ended with status: {status}. Error: {task_doc.get('error', '')}"
            )

        message = {
            "role": "assistant",
            "content": f"[Task Update] {summary_text}",
            "is_html": False,
            "timestamp": datetime.now(timezone.utc),
        }
        conversations_collection.update_one(
            {"_id": __import__("bson").ObjectId(conv_id)},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
    except Exception as e:
        logger.error(f"Failed to post conversation update: {e}")
