from typing import Optional, Dict, Any
from db.user_profiles_crud import get_user_profile, upsert_user_profile, delete_user_profile
from core.user_context_models import UserProfileCreatePayload, UserProfileUpdatePayload
from core.config import get_logger

logger = get_logger("user_profile_service")

async def get_user_profile_service(user_id: str = "default") -> Optional[Dict[str, Any]]:
    try:
        return get_user_profile(user_id)
    except Exception as e:
        logger.error(f"Error getting user profile for {user_id}: {e}")
        return None

async def upsert_user_profile_service(payload: UserProfileCreatePayload | UserProfileUpdatePayload, user_id: str = "default") -> Optional[Dict[str, Any]]:
    try:
        data = payload.dict(exclude_unset=True)
        return upsert_user_profile(data, user_id)
    except Exception as e:
        logger.error(f"Error upserting user profile for {user_id}: {e}")
        return None

async def delete_user_profile_service(user_id: str = "default") -> bool:
    try:
        return delete_user_profile(user_id)
    except Exception as e:
        logger.error(f"Error deleting user profile for {user_id}: {e}")
        return False

