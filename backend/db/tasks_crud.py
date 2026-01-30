from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from bson import ObjectId

from db.mongodb import get_tasks_collection


def _obj_id(task_id: str) -> ObjectId:
    if not ObjectId.is_valid(task_id):
        raise ValueError("Invalid task id")
    return ObjectId(task_id)


def create_indexes():
    col = get_tasks_collection()
    col.create_index("status")
    col.create_index([("updated_at", -1)])


def create_task(doc: Dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    doc.setdefault("created_at", now)
    doc.setdefault("updated_at", now)
    res = get_tasks_collection().insert_one(doc)
    return str(res.inserted_id)


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    return get_tasks_collection().find_one({"_id": _obj_id(task_id)})


def list_tasks(limit: int = 50) -> List[Dict[str, Any]]:
    cur = get_tasks_collection().find({}, {"plan": 0}).sort("updated_at", -1).limit(limit)
    return list(cur)


def update_task(task_id: str, patch: Dict[str, Any]) -> None:
    patch = {**patch, "updated_at": datetime.now(timezone.utc)}
    get_tasks_collection().update_one({"_id": _obj_id(task_id)}, {"$set": patch})


def set_step_status(task_id: str, idx: int, patch: Dict[str, Any]) -> None:
    # Update nested plan.steps[idx]
    updates = {f"plan.steps.{idx}.{k}": v for k, v in patch.items()}
    updates["updated_at"] = datetime.now(timezone.utc)
    get_tasks_collection().update_one({"_id": _obj_id(task_id)}, {"$set": updates})


def increment_usage(task_id: str, field: str, delta: int) -> None:
    get_tasks_collection().update_one(
        {"_id": _obj_id(task_id)},
        {"$inc": {f"usage.{field}": delta}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )

