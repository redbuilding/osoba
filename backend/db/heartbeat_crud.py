from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any, List
from bson import ObjectId
from db.mongodb import get_heartbeat_insights_collection
from core.config import get_logger

logger = get_logger("heartbeat_crud")


def _serialize(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Serialize MongoDB document by converting ObjectId to string."""
    if not doc:
        return None
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def create_insight(insight_data: Dict[str, Any], user_id: str = "default") -> Optional[Dict[str, Any]]:
    """Create a new proactive insight."""
    try:
        collection = get_heartbeat_insights_collection()
        now = datetime.now(timezone.utc)
        
        insight_doc = {
            "user_id": user_id,
            "insight_type": insight_data.get("insight_type", "task_suggestion"),
            "title": insight_data["title"],
            "description": insight_data["description"],
            "action_data": insight_data.get("action_data"),
            "dismissed": False,
            "created_at": now,
        }
        
        result = collection.insert_one(insight_doc)
        insight_doc["_id"] = result.inserted_id
        logger.info(f"Created insight {result.inserted_id} for user {user_id}")
        return _serialize(insight_doc)
    except Exception as e:
        logger.error(f"Error creating insight for {user_id}: {e}")
        return None


def get_insights(user_id: str = "default", limit: int = 50, dismissed: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Get insights for a user with optional filtering."""
    try:
        collection = get_heartbeat_insights_collection()
        query = {"user_id": user_id}
        
        if dismissed is not None:
            query["dismissed"] = dismissed
        
        insights = list(collection.find(query).sort("created_at", -1).limit(limit))
        return [_serialize(insight) for insight in insights]
    except Exception as e:
        logger.error(f"Error getting insights for {user_id}: {e}")
        return []


def get_insight_by_id(insight_id: str, user_id: str = "default") -> Optional[Dict[str, Any]]:
    """Get a specific insight by ID."""
    try:
        collection = get_heartbeat_insights_collection()
        insight = collection.find_one({"_id": ObjectId(insight_id), "user_id": user_id})
        return _serialize(insight)
    except Exception as e:
        logger.error(f"Error getting insight {insight_id}: {e}")
        return None
            query["dismissed"] = dismissed
        
        cursor = collection.find(query).sort("created_at", -1).limit(limit)
        insights = [_serialize(doc) for doc in cursor]
        return insights
    except Exception as e:
        logger.error(f"Error getting insights for {user_id}: {e}")
        return []


def dismiss_insight(insight_id: str, user_id: str = "default") -> bool:
    """Dismiss an insight."""
    try:
        if not ObjectId.is_valid(insight_id):
            return False
        
        collection = get_heartbeat_insights_collection()
        result = collection.update_one(
            {"_id": ObjectId(insight_id), "user_id": user_id},
            {"$set": {"dismissed": True}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Dismissed insight {insight_id} for user {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error dismissing insight {insight_id}: {e}")
        return False


def count_insights_today(user_id: str = "default") -> int:
    """Count non-dismissed insights created today for a user."""
    try:
        collection = get_heartbeat_insights_collection()
        
        # Get start of today in UTC
        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        
        count = collection.count_documents({
            "user_id": user_id,
            "dismissed": False,
            "created_at": {"$gte": start_of_day}
        })
        
        return count
    except Exception as e:
        logger.error(f"Error counting insights for {user_id}: {e}")
        return 0
