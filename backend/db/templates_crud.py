from typing import List, Dict, Any, Optional
from bson import ObjectId
from db.mongodb import get_templates_collection

def create_template(template_data: dict) -> str:
    """Create a new task template."""
    collection = get_templates_collection()
    result = collection.insert_one(template_data)
    return str(result.inserted_id)

def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Get a template by ID."""
    if not ObjectId.is_valid(template_id):
        return None
    collection = get_templates_collection()
    return collection.find_one({"_id": ObjectId(template_id)})

def list_templates(category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """List templates, optionally filtered by category."""
    collection = get_templates_collection()
    query = {"category": category} if category else {}
    cursor = collection.find(query).sort("created_at", -1).limit(limit)
    return list(cursor)

def update_template(template_id: str, patch: Dict[str, Any]) -> None:
    """Update a template."""
    if not ObjectId.is_valid(template_id):
        return
    collection = get_templates_collection()
    collection.update_one({"_id": ObjectId(template_id)}, {"$set": patch})

def delete_template(template_id: str) -> bool:
    """Delete a template."""
    if not ObjectId.is_valid(template_id):
        return False
    collection = get_templates_collection()
    result = collection.delete_one({"_id": ObjectId(template_id)})
    return result.deleted_count > 0
