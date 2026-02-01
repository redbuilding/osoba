from typing import List
from fastapi import APIRouter, HTTPException
from core.profile_models import ProfileCreatePayload, ProfileUpdatePayload, ProfileResponse, AIProfile
from services.profile_service import (
    get_profiles_for_user, get_profile_by_id_service, get_active_profile_service,
    create_profile_service, update_profile_service, delete_profile_service,
    set_active_profile_service
)
from core.config import get_logger

logger = get_logger("profiles_api")
router = APIRouter()

@router.get("/api/profiles")
async def list_profiles(user_id: str = "default"):
    """Get all profiles for a user."""
    try:
        profiles = await get_profiles_for_user(user_id)
        return {"profiles": profiles}
    except Exception as e:
        logger.error(f"Error listing profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/profiles/active")
async def get_active_profile(user_id: str = "default"):
    """Get the active profile for a user."""
    try:
        profile = await get_active_profile_service(user_id)
        return {"profile": profile}
    except Exception as e:
        logger.error(f"Error getting active profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: str, user_id: str = "default"):
    """Get a specific profile by ID."""
    try:
        profile = await get_profile_by_id_service(profile_id, user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"profile": profile}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/profiles")
async def create_profile(payload: ProfileCreatePayload, user_id: str = "default"):
    """Create a new profile."""
    try:
        profile_id = await create_profile_service(payload, user_id)
        if not profile_id:
            return ProfileResponse(
                success=False,
                message="Failed to create profile. Check if you've reached the limit (3 profiles) or if the name already exists."
            )
        
        return ProfileResponse(
            success=True,
            message="Profile created successfully",
            profile_id=profile_id
        )
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        return ProfileResponse(
            success=False,
            message=f"Error creating profile: {str(e)}"
        )

@router.put("/api/profiles/{profile_id}")
async def update_profile(profile_id: str, payload: ProfileUpdatePayload, user_id: str = "default"):
    """Update an existing profile."""
    try:
        success = await update_profile_service(profile_id, payload, user_id)
        if not success:
            return ProfileResponse(
                success=False,
                message="Failed to update profile. Profile may not exist or name may already be taken."
            )
        
        return ProfileResponse(
            success=True,
            message="Profile updated successfully"
        )
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return ProfileResponse(
            success=False,
            message=f"Error updating profile: {str(e)}"
        )

@router.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: str, user_id: str = "default"):
    """Delete a profile."""
    try:
        success = await delete_profile_service(profile_id, user_id)
        if not success:
            return ProfileResponse(
                success=False,
                message="Failed to delete profile. Profile may not exist."
            )
        
        return ProfileResponse(
            success=True,
            message="Profile deleted successfully"
        )
    except Exception as e:
        logger.error(f"Error deleting profile: {e}")
        return ProfileResponse(
            success=False,
            message=f"Error deleting profile: {str(e)}"
        )

@router.post("/api/profiles/{profile_id}/activate")
async def activate_profile(profile_id: str, user_id: str = "default"):
    """Set a profile as active."""
    try:
        success = await set_active_profile_service(profile_id, user_id)
        if not success:
            return ProfileResponse(
                success=False,
                message="Failed to activate profile. Profile may not exist."
            )
        
        return ProfileResponse(
            success=True,
            message="Profile activated successfully"
        )
    except Exception as e:
        logger.error(f"Error activating profile: {e}")
        return ProfileResponse(
            success=False,
            message=f"Error activating profile: {str(e)}"
        )

@router.post("/api/profiles/deactivate")
async def deactivate_all_profiles(user_id: str = "default"):
    """Deactivate all profiles (use default behavior)."""
    try:
        success = await set_active_profile_service(None, user_id)
        if not success:
            return ProfileResponse(
                success=False,
                message="Failed to deactivate profiles."
            )
        
        return ProfileResponse(
            success=True,
            message="All profiles deactivated successfully"
        )
    except Exception as e:
        logger.error(f"Error deactivating profiles: {e}")
        return ProfileResponse(
            success=False,
            message=f"Error deactivating profiles: {str(e)}"
        )
