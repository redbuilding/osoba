from datetime import datetime, timezone
from typing import Dict, Optional, Any
from bson import ObjectId
from db.mongodb import get_user_profiles_collection
from core.config import get_logger

logger = get_logger("user_profiles_crud")

def _serialize(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def get_user_profile(user_id: str = "default") -> Optional[Dict[str, Any]]:
    """Get the single user profile document for a user."""
    try:
        collection = get_user_profiles_collection()
        doc = collection.find_one({"user_id": user_id})
        return _serialize(doc)
    except Exception as e:
        logger.error(f"Error getting user profile for {user_id}: {e}")
        return None

def upsert_user_profile(profile_data: Dict[str, Any], user_id: str = "default") -> Optional[Dict[str, Any]]:
    """Create or update the user profile document for a user and return it."""
    try:
        collection = get_user_profiles_collection()
        now = datetime.now(timezone.utc)

        # Only $set fields that were actually provided (exclude_unset already applied upstream)
        update_doc = {k: v for k, v in profile_data.items() if k not in ("_id", "created_at")}
        update_doc["user_id"] = user_id
        update_doc["updated_at"] = now

        # Upsert and set created_at if inserting
        result = collection.update_one(
            {"user_id": user_id},
            {"$set": update_doc, "$setOnInsert": {"created_at": now}},
            upsert=True
        )

        # Fetch the updated document
        doc = collection.find_one({"user_id": user_id})
        return _serialize(doc)
    except Exception as e:
        logger.error(f"Error upserting user profile for {user_id}: {e}")
        return None

def delete_user_profile(user_id: str = "default") -> bool:
    """Delete the user profile document for a user."""
    try:
        collection = get_user_profiles_collection()
        result = collection.delete_one({"user_id": user_id})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting user profile for {user_id}: {e}")
        return False

