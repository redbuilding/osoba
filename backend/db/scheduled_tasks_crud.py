from typing import List, Dict, Any, Optional
from bson import ObjectId
from db.mongodb import get_scheduled_tasks_collection

def create_scheduled_task(task_data: dict) -> str:
    """Create a new scheduled task."""
    collection = get_scheduled_tasks_collection()
    result = collection.insert_one(task_data)
    return str(result.inserted_id)

def get_scheduled_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Get a scheduled task by ID."""
    if not ObjectId.is_valid(task_id):
        return None
    collection = get_scheduled_tasks_collection()
    return collection.find_one({"_id": ObjectId(task_id)})

def list_scheduled_tasks(limit: int = 50) -> List[Dict[str, Any]]:
    """List all scheduled tasks."""
    collection = get_scheduled_tasks_collection()
    cursor = collection.find().sort("created_at", -1).limit(limit)
    return list(cursor)

def update_scheduled_task(task_id: str, patch: Dict[str, Any]) -> None:
    """Update a scheduled task."""
    if not ObjectId.is_valid(task_id):
        return
    collection = get_scheduled_tasks_collection()
    collection.update_one({"_id": ObjectId(task_id)}, {"$set": patch})

def delete_scheduled_task(task_id: str) -> bool:
    """Delete a scheduled task."""
    if not ObjectId.is_valid(task_id):
        return False
    collection = get_scheduled_tasks_collection()
    result = collection.delete_one({"_id": ObjectId(task_id)})
    return result.deleted_count > 0
