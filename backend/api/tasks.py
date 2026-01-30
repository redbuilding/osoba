from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from core.models import TaskCreatePayload, TaskSummary, TaskDetail
from core.config import get_logger
from db.tasks_crud import create_task, list_tasks, get_task, update_task, create_indexes
from services.progress_bus import progress_bus


router = APIRouter()
logger = get_logger("api_tasks")


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
    doc = {
        "title": payload.goal[:60] or "Task",
        "goal": payload.goal,
        "status": "PLANNING" if payload.dry_run else "PLANNING",
        "created_at": now,
        "updated_at": now,
        "conversation_id": payload.conversation_id,
        "ollama_model_name": payload.ollama_model_name,
        "budget": payload.budget or {},
        "usage": {"tool_calls": 0, "seconds_elapsed": 0},
        "current_step_index": -1,
    }
    tid = create_task(doc)
    # If not dry_run, dispatcher will pick and convert to PENDING/RUNNING
    doc = get_task(tid)
    if not doc:
        raise HTTPException(status_code=500, detail="Failed to create task")
    doc["_id"] = str(doc["_id"])
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
