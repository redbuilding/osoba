from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from core.models import TaskCreatePayload, TaskSummary, TaskDetail
from db.mongodb import get_conversations_collection
from core.config import get_logger
from db.tasks_crud import create_task, list_tasks, get_task, update_task, create_indexes, get_queue_position
from services.progress_bus import progress_bus


router = APIRouter()
logger = get_logger("api_tasks")

MAX_KB_DOCS = 2
MAX_CHARS_PER_DOC = 4_000


def _build_task_kb_context(doc_ids: List[str]):
    """Fetch up to 2 indexed KB docs, snapshot content, return (kb_docs list, kb_context string)."""
    from db.documents_crud import get_document
    parts, kb_docs = [], []
    for doc_id in doc_ids[:MAX_KB_DOCS]:
        try:
            doc = get_document(doc_id)
        except Exception:
            continue
        if not doc or not doc.get("indexed"):
            continue
        title = doc.get("title", "Untitled")
        excerpt = (doc.get("content") or "")[:MAX_CHARS_PER_DOC]
        parts.append(f"[{title}]\n{excerpt}")
        kb_docs.append({"id": doc_id, "title": title})
    if not parts:
        return [], ""
    return kb_docs, "=== Knowledge Base ===\n" + "\n\n".join(parts)


@router.on_event("startup")
def _ensure_indexes():
    try:
        create_indexes()
    except Exception:
        logger.warning("Could not create task indexes; continuing.")


@router.post("/api/tasks", response_model=TaskDetail, response_model_by_alias=False)
async def create_task_endpoint(payload: TaskCreatePayload):
    if not payload.goal:
        raise HTTPException(status_code=400, detail="Missing goal")
    now = datetime.now(timezone.utc)
    # Resolve model_name
    resolved_model = payload.model_name
    # If launched from a conversation and no model provided, inherit the conversation's model
    if not resolved_model and payload.conversation_id:
        try:
            conv = get_conversations_collection().find_one({"_id": __import__('bson').ObjectId(payload.conversation_id)})
            if conv:
                resolved_model = conv.get("model_name") or conv.get("ollama_model_name")
        except Exception:
            resolved_model = resolved_model or None
    kb_docs = []
    kb_context = ""
    if payload.kb_doc_ids:
        kb_docs, kb_context = _build_task_kb_context(payload.kb_doc_ids)
    doc = {
        "title": payload.goal[:60] or "Task",
        "goal": payload.goal,
        "status": "PLANNING" if payload.dry_run else "PLANNING",
        "created_at": now,
        "updated_at": now,
        "conversation_id": payload.conversation_id,
        "model_name": resolved_model,
        "budget": payload.budget or {},
        "usage": {"tool_calls": 0, "seconds_elapsed": 0},
        "current_step_index": -1,
        "priority": payload.priority,
        "kb_docs": kb_docs,
        "kb_context": kb_context,
    }
    tid = create_task(doc)
    # If not dry_run, dispatcher will pick and convert to PENDING/RUNNING
    doc = get_task(tid)
    if not doc:
        raise HTTPException(status_code=500, detail="Failed to create task")
    doc["_id"] = str(doc["_id"])
    
    # Add queue position for user feedback
    try:
        queue_position = get_queue_position(tid)
        if queue_position > 1:
            doc["queue_position"] = queue_position
    except Exception:
        # In test/memory mode or if DB unavailable, skip queue position
        pass
    
    return TaskDetail.model_validate(doc)


@router.get("/api/tasks", response_model=List[TaskSummary], response_model_by_alias=False)
async def list_tasks_endpoint():
    items = list_tasks()
    for it in items:
        it["_id"] = str(it["_id"])  # for Pydantic aliasing
    return [TaskSummary.model_validate(it) for it in items]


@router.get("/api/tasks/{task_id}", response_model=TaskDetail, response_model_by_alias=False)
async def get_task_detail(task_id: str):
    doc = get_task(task_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Task not found")
    # Defensive normalization: ensure plan steps have required fields to avoid validation errors
    try:
        plan = (doc.get("plan") or {})
        steps = plan.get("steps")
        if isinstance(steps, list):
            normalized = []
            for i, st in enumerate(steps):
                if not isinstance(st, dict):
                    st = {}
                st.setdefault("id", st.get("id") or f"s{i+1}")
                st.setdefault("title", st.get("title") or st.get("tool") or f"Step {i+1}")
                st.setdefault("instruction", st.get("instruction") or "")
                st.setdefault("tool", st.get("tool") or "unknown")
                st.setdefault("params", st.get("params") or {})
                st.setdefault("success_criteria", st.get("success_criteria") or "")
                st.setdefault("max_retries", int(st.get("max_retries") or 1))
                normalized.append(st)
            plan["steps"] = normalized
            doc["plan"] = plan
    except Exception:
        # If anything goes wrong, continue with raw doc; the UI can still render
        pass
    doc["_id"] = str(doc["_id"])  # for Pydantic aliasing
    return TaskDetail.model_validate(doc)


@router.get("/api/tasks/{task_id}/stream")
async def stream_task(task_id: str, request: Request):
    # SSE stream of progress events
    async def event_gen():
        async for event in progress_bus.subscribe(task_id):
            # If client disconnects, exit
            if await request.is_disconnected():
                break
            yield event

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post("/api/tasks/{task_id}/pause")
async def pause_task(task_id: str):
    if not get_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    update_task(task_id, {"status": "PAUSED"})
    await progress_bus.publish(task_id, {"type": "TASK_STATUS", "task_id": task_id, "status": "PAUSED"})
    return {"status": "PAUSED"}


@router.post("/api/tasks/{task_id}/resume")
async def resume_task(task_id: str):
    if not get_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    update_task(task_id, {"status": "PENDING"})
    await progress_bus.publish(task_id, {"type": "TASK_STATUS", "task_id": task_id, "status": "PENDING"})
    return {"status": "PENDING"}


@router.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    if not get_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    update_task(task_id, {"status": "CANCELED"})
    await progress_bus.publish(task_id, {"type": "TASK_STATUS", "task_id": task_id, "status": "CANCELED"})
    return {"status": "CANCELED"}


@router.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    from db.tasks_crud import delete_task as delete_task_db
    if not get_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    delete_task_db(task_id)
    return {"deleted": True}
