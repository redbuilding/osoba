from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from db.mongodb import get_profiles_collection
from core.config import get_logger

logger = get_logger("profiles_crud")

MAX_PROFILES_PER_USER = 3

def get_user_profiles(user_id: str = "default") -> List[Dict[str, Any]]:
    """Get all profiles for a user, sorted by creation date."""
    try:
        collection = get_profiles_collection()
        cursor = collection.find({"user_id": user_id}).sort("created_at", -1)
        profiles = list(cursor)
        
        # Convert ObjectId to string for JSON serialization
        for profile in profiles:
            if "_id" in profile:
                profile["_id"] = str(profile["_id"])
        
        return profiles
    except Exception as e:
        logger.error(f"Error getting user profiles: {e}")
        return []

def get_profile_by_id(profile_id: str, user_id: str = "default") -> Optional[Dict[str, Any]]:
    """Get a specific profile by ID, ensuring user ownership."""
    try:
        if not ObjectId.is_valid(profile_id):
            return None
        
        collection = get_profiles_collection()
        profile = collection.find_one({
            "_id": ObjectId(profile_id),
            "user_id": user_id
        })
        
        if profile and "_id" in profile:
            profile["_id"] = str(profile["_id"])
        
        return profile
    except Exception as e:
        logger.error(f"Error getting profile by ID: {e}")
        return None

def get_active_profile(user_id: str = "default") -> Optional[Dict[str, Any]]:
    """Get the currently active profile for a user."""
    try:
        collection = get_profiles_collection()
        profile = collection.find_one({
            "user_id": user_id,
            "is_active": True
        })
        
        if profile and "_id" in profile:
            profile["_id"] = str(profile["_id"])
        
        return profile
    except Exception as e:
        logger.error(f"Error getting active profile: {e}")
        return None

def create_profile(profile_data: Dict[str, Any], user_id: str = "default") -> Optional[str]:
    """Create a new profile for a user."""
    try:
        collection = get_profiles_collection()
        
        # Check profile limit
        existing_count = collection.count_documents({"user_id": user_id})
        if existing_count >= MAX_PROFILES_PER_USER:
            logger.warning(f"User {user_id} has reached maximum profile limit ({MAX_PROFILES_PER_USER})")
            return None
        
        # Check name uniqueness for user
        existing_profile = collection.find_one({
            "user_id": user_id,
            "name": profile_data["name"]
        })
        if existing_profile:
            logger.warning(f"Profile name '{profile_data['name']}' already exists for user {user_id}")
            return None
        
        # Prepare profile document
        now = datetime.now(timezone.utc)
        profile_doc = {
            "name": profile_data["name"],
            "communication_style": profile_data["communication_style"],
            "expertise_areas": profile_data.get("expertise_areas", []),
            "backstory": profile_data.get("backstory") or None,
            "user_id": user_id,
            "is_active": False,  # New profiles start inactive
            "created_at": now,
            "updated_at": now
        }
        
        result = collection.insert_one(profile_doc)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        return None

def update_profile(profile_id: str, update_data: Dict[str, Any], user_id: str = "default") -> bool:
    """Update an existing profile."""
    try:
        if not ObjectId.is_valid(profile_id):
            return False
        
        collection = get_profiles_collection()
        
        # Check if profile exists and belongs to user
        existing_profile = collection.find_one({
            "_id": ObjectId(profile_id),
            "user_id": user_id
        })
        if not existing_profile:
            return False
        
        # Check name uniqueness if name is being updated
        if "name" in update_data:
            name_conflict = collection.find_one({
                "user_id": user_id,
                "name": update_data["name"],
                "_id": {"$ne": ObjectId(profile_id)}
            })
            if name_conflict:
                logger.warning(f"Profile name '{update_data['name']}' already exists for user {user_id}")
                return False
        
        # Handle active profile switching
        if update_data.get("is_active") is True:
            # Deactivate all other profiles for this user
            collection.update_many(
                {"user_id": user_id, "_id": {"$ne": ObjectId(profile_id)}},
                {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
            )
        
        # Update the profile
        update_data["updated_at"] = datetime.now(timezone.utc)
        result = collection.update_one(
            {"_id": ObjectId(profile_id), "user_id": user_id},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return False

def delete_profile(profile_id: str, user_id: str = "default") -> bool:
    """Delete a profile."""
    try:
        if not ObjectId.is_valid(profile_id):
            return False
        
        collection = get_profiles_collection()
        result = collection.delete_one({
            "_id": ObjectId(profile_id),
            "user_id": user_id
        })
        
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting profile: {e}")
        return False

def set_active_profile(profile_id: Optional[str], user_id: str = "default") -> bool:
    """Set the active profile for a user. Pass None to deactivate all profiles."""
    try:
        collection = get_profiles_collection()
        
        # Deactivate all profiles for this user
        collection.update_many(
            {"user_id": user_id},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
        )
        
        # Activate the specified profile if provided
        if profile_id:
            if not ObjectId.is_valid(profile_id):
                return False
            
            result = collection.update_one(
                {"_id": ObjectId(profile_id), "user_id": user_id},
                {"$set": {"is_active": True, "updated_at": datetime.now(timezone.utc)}}
            )
            
            return result.modified_count > 0
        
        return True  # Successfully deactivated all profiles
    except Exception as e:
        logger.error(f"Error setting active profile: {e}")
        return False
