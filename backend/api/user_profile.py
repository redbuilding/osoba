from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from core.user_context_models import UserProfileCreatePayload, UserProfileUpdatePayload
from services.user_profile_service import (
    get_user_profile_service,
    upsert_user_profile_service,
    delete_user_profile_service,
)
from core.config import get_logger

logger = get_logger("user_profile_api")
router = APIRouter()

class UserProfileResponse(BaseModel):
    success: bool
    message: str
    profile: Optional[Dict[str, Any]] = None

@router.get("/api/user-profile")
async def get_user_profile(user_id: str = "default"):
    try:
        profile = await get_user_profile_service(user_id)
        return UserProfileResponse(success=True, message="OK", profile=profile)
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/user-profile")
async def put_user_profile(payload: UserProfileUpdatePayload | UserProfileCreatePayload, user_id: str = "default"):
    try:
        profile = await upsert_user_profile_service(payload, user_id)
        if not profile:
            return UserProfileResponse(success=False, message="Failed to save user profile")
        return UserProfileResponse(success=True, message="Profile saved", profile=profile)
    except Exception as e:
        logger.error(f"Error saving user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/user-profile")
async def delete_user_profile(user_id: str = "default"):
    try:
        success = await delete_user_profile_service(user_id)
        if not success:
            return UserProfileResponse(success=False, message="No profile to delete", profile=None)
        return UserProfileResponse(success=True, message="Profile deleted", profile=None)
    except Exception as e:
        logger.error(f"Error deleting user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

