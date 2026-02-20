from fastapi import APIRouter, HTTPException
from typing import List, Optional
from core.heartbeat_models import ProactiveInsight, HeartbeatConfigUpdate, InsightCreatePayload
from db.heartbeat_crud import get_insights, dismiss_insight
from db.user_profiles_crud import get_user_profile, upsert_user_profile
from services.heartbeat_service import heartbeat_service

router = APIRouter(prefix="/api/heartbeat", tags=["heartbeat"])


@router.get("/insights")
async def get_insights_endpoint(user_id: str = "default", limit: int = 50, dismissed: Optional[bool] = None):
    """Get proactive insights for a user."""
    try:
        insights = get_insights(user_id, limit, dismissed)
        return {"insights": insights}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving insights: {str(e)}")


@router.post("/insights/{insight_id}/dismiss")
async def dismiss_insight_endpoint(insight_id: str, user_id: str = "default"):
    """Dismiss a proactive insight."""
    try:
        success = dismiss_insight(insight_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Insight not found or already dismissed")
        return {"status": "success", "message": "Insight dismissed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error dismissing insight: {str(e)}")


@router.get("/config")
async def get_config_endpoint(user_id: str = "default"):
    """Get heartbeat configuration for a user."""
    try:
        profile = get_user_profile(user_id)
        if not profile:
            return {"config": {
                "enabled": True,
                "interval": "2h",
                "model_name": "anthropic/claude-haiku-4-5",
                "max_insights_per_day": 5
            }}
        
        config = profile.get("heartbeat_config", {
            "enabled": True,
            "interval": "2h",
            "model_name": "anthropic/claude-haiku-4-5",
            "max_insights_per_day": 5
        })
        return {"config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving config: {str(e)}")


@router.put("/config")
async def update_config_endpoint(config: HeartbeatConfigUpdate, user_id: str = "default"):
    """Update heartbeat configuration for a user."""
    try:
        profile = get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Get existing config
        current_config = profile.get("heartbeat_config", {})
        
        # Update with new values
        update_data = config.model_dump(exclude_unset=True)
        current_config.update(update_data)
        
        # Update profile
        profile["heartbeat_config"] = current_config
        updated = upsert_user_profile(profile, user_id)
        
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update config")
        
        return {"status": "success", "config": current_config}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")


@router.post("/trigger")
async def trigger_heartbeat_endpoint(user_id: str = "default"):
    """Manually trigger a heartbeat (for testing)."""
    try:
        await heartbeat_service.run_heartbeat(user_id)
        return {"status": "success", "message": "Heartbeat triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering heartbeat: {str(e)}")
