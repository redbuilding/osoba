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


@router.get("/context-config")
async def get_context_config_endpoint(user_id: str = "default"):
    """Get context gathering configuration."""
    try:
        profile = get_user_profile(user_id)
        if not profile:
            return {"context_sources": {
                "memory": True,
                "git": True,
                "project": False,
                "system": False
            }}
        
        config = profile.get("heartbeat_config", {})
        context_sources = config.get("context_sources", {
            "memory": True,
            "git": True,
            "project": False,
            "system": False
        })
        return {"context_sources": context_sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving context config: {str(e)}")


@router.put("/context-config")
async def update_context_config_endpoint(context_sources: dict, user_id: str = "default"):
    """Update context gathering configuration."""
    try:
        profile = get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Get existing config
        current_config = profile.get("heartbeat_config", {})
        current_config["context_sources"] = context_sources
        
        # Update profile
        profile["heartbeat_config"] = current_config
        updated = upsert_user_profile(profile, user_id)
        
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update context config")
        
        return {"status": "success", "context_sources": context_sources}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating context config: {str(e)}")


@router.post("/insights/{insight_id}/create-task")
async def create_task_from_insight_endpoint(insight_id: str, user_id: str = "default"):
    """Convert a heartbeat insight into a tracked task."""
    try:
        from db.heartbeat_crud import get_insight_by_id, get_heartbeat_config
        from db.tasks_crud import create_task, get_task
        from datetime import datetime, timezone
        
        # Get the insight
        insight = get_insight_by_id(insight_id, user_id)
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")
        
        # Get heartbeat config for model selection
        heartbeat_config = get_heartbeat_config(user_id)
        model_name = heartbeat_config.get("model_name") if heartbeat_config else None
        
        # Create task with proper schema
        goal = insight.get("title", "Heartbeat Task")
        task_data = {
            "title": goal[:60],
            "goal": goal,
            "status": "PLANNING",
            "priority": 2,
            "budget": {},
            "usage": {"tool_calls": 0, "seconds_elapsed": 0},
            "current_step_index": -1,
            "model_name": model_name,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "metadata": {
                "source": "heartbeat",
                "insight_id": insight_id,
                "description": insight.get("description", "")
            }
        }
        
        task_id = create_task(task_data)
        task = get_task(task_id)
        if not task:
            raise HTTPException(status_code=500, detail="Failed to create task")
        
        task["_id"] = str(task["_id"])
        return {"status": "success", "task_id": task_id, "task": task}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating task from insight: {str(e)}")


@router.get("/file-status")
async def get_file_status_endpoint():
    """Get status of HEARTBEAT.md file"""
    try:
        from services.heartbeat_file_parser import get_heartbeat_file_parser
        
        parser = get_heartbeat_file_parser()
        exists = parser.exists()
        
        if not exists:
            return {
                "exists": False,
                "file_path": None,
                "tasks": [],
                "errors": []
            }
        
        # Parse file
        tasks = parser.parse()
        errors = parser.validate(tasks)
        
        return {
            "exists": True,
            "file_path": parser.file_path,
            "tasks": tasks,
            "task_count": len(tasks),
            "errors": errors,
            "valid": len(errors) == 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking file status: {str(e)}")


@router.post("/sync-from-file")
async def sync_from_file_endpoint(user_id: str = "default"):
    """Sync heartbeat configuration from HEARTBEAT.md file to database"""
    try:
        from services.heartbeat_file_parser import get_heartbeat_file_parser
        
        parser = get_heartbeat_file_parser()
        if not parser.exists():
            raise HTTPException(status_code=404, detail="HEARTBEAT.md file not found")
        
        # Parse and validate
        tasks = parser.parse()
        errors = parser.validate(tasks)
        
        if errors:
            return {
                "status": "error",
                "message": "Validation errors found",
                "errors": errors
            }
        
        # Update profile with file-based tasks
        profile = get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        current_config = profile.get("heartbeat_config", {})
        current_config["file_tasks"] = tasks
        current_config["file_sync_enabled"] = True
        
        profile["heartbeat_config"] = current_config
        updated = upsert_user_profile(profile, user_id)
        
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to sync configuration")
        
        return {
            "status": "success",
            "message": f"Synced {len(tasks)} tasks from file",
            "tasks": tasks
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing from file: {str(e)}")


@router.post("/sync-to-file")
async def sync_to_file_endpoint(user_id: str = "default"):
    """Sync heartbeat configuration from database to HEARTBEAT.md file"""
    try:
        from services.heartbeat_file_parser import get_heartbeat_file_parser
        
        # Get current config
        profile = get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        config = profile.get("heartbeat_config", {})
        file_tasks = config.get("file_tasks", [])
        
        if not file_tasks:
            raise HTTPException(status_code=400, detail="No file tasks configured")
        
        # Write to file
        parser = get_heartbeat_file_parser()
        success = parser.write(file_tasks)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to write file")
        
        return {
            "status": "success",
            "message": f"Wrote {len(file_tasks)} tasks to {parser.file_path}",
            "file_path": parser.file_path
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing to file: {str(e)}")
