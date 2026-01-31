from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.provider_service import (
    get_available_models_by_provider, get_provider_status, validate_provider_api_key
)
from db.settings_crud import (
    get_user_settings, update_provider_api_key, remove_provider_api_key, 
    validate_provider_settings
)
from core.providers import get_available_providers, get_provider_display_name
from core.config import get_logger

logger = get_logger("providers_api")
router = APIRouter()

class ProviderSettingsPayload(BaseModel):
    provider: str
    api_key: str

class ProviderSettingsResponse(BaseModel):
    success: bool
    message: str
    validation: Dict[str, Any] = None

@router.get("/api/providers")
async def list_providers():
    """Get list of all available providers with their status."""
    try:
        providers = []
        for provider_id in get_available_providers():
            status = await get_provider_status(provider_id)
            providers.append({
                "id": provider_id,
                "name": get_provider_display_name(provider_id),
                "status": status
            })
        
        return {"providers": providers}
    except Exception as e:
        logger.error(f"Error listing providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/providers/models")
async def list_provider_models():
    """Get available models grouped by provider."""
    try:
        models_by_provider = await get_available_models_by_provider()
        
        # Format response with provider information
        response = {}
        for provider_id, models in models_by_provider.items():
            provider_status = await get_provider_status(provider_id)
            # Only expose non-Ollama models if provider is configured
            if provider_id != 'ollama' and not provider_status.get("configured"):
                models = []
            response[provider_id] = {
                "name": get_provider_display_name(provider_id),
                "models": models,
                "status": provider_status
            }
        
        return {"providers": response}
    except Exception as e:
        logger.error(f"Error listing provider models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/providers/{provider_id}/status")
async def get_provider_status_endpoint(provider_id: str, user_id: str = "default"):
    """Get status for a specific provider."""
    try:
        status = await get_provider_status(provider_id, user_id)
        return {"provider": provider_id, "status": status}
    except Exception as e:
        logger.error(f"Error getting provider status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/providers/settings")
async def save_provider_settings(payload: ProviderSettingsPayload, user_id: str = "default"):
    """Save API key for a provider."""
    try:
        provider_id = payload.provider
        api_key = payload.api_key.strip()
        
        if not api_key:
            return ProviderSettingsResponse(
                success=False,
                message="API key cannot be empty"
            )
        
        # Validate the API key by making a test request
        validation_result = await validate_provider_api_key(provider_id, api_key)
        
        if not validation_result.get("valid", False):
            return ProviderSettingsResponse(
                success=False,
                message=validation_result.get("error", "API key validation failed"),
                validation=validation_result
            )
        
        # Save the API key
        success = update_provider_api_key(provider_id, api_key, user_id)
        
        if success:
            return ProviderSettingsResponse(
                success=True,
                message="API key saved and validated successfully",
                validation=validation_result
            )
        else:
            return ProviderSettingsResponse(
                success=False,
                message="Failed to save API key"
            )
            
    except Exception as e:
        logger.error(f"Error saving provider settings: {e}")
        return ProviderSettingsResponse(
            success=False,
            message=f"Error saving settings: {str(e)}"
        )

@router.delete("/api/providers/{provider_id}/settings")
async def remove_provider_settings(provider_id: str, user_id: str = "default"):
    """Remove API key for a provider."""
    try:
        success = remove_provider_api_key(provider_id, user_id)
        
        if success:
            return {"success": True, "message": "API key removed successfully"}
        else:
            return {"success": False, "message": "Failed to remove API key"}
            
    except Exception as e:
        logger.error(f"Error removing provider settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/providers/{provider_id}/validate")
async def validate_provider_settings_endpoint(provider_id: str, user_id: str = "default"):
    """Validate provider settings without exposing the API key."""
    try:
        validation = validate_provider_settings(provider_id, user_id)
        return {"provider": provider_id, "validation": validation}
    except Exception as e:
        logger.error(f"Error validating provider settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/settings")
async def get_user_settings_endpoint(user_id: str = "default"):
    """Get user settings (without exposing API keys)."""
    try:
        settings = get_user_settings(user_id)
        
        if not settings:
            return {"settings": {"providers": {}}}
        
        # Remove API keys from response for security and ensure JSON-serializable values
        safe_settings = settings.copy()
        # Drop Mongo ObjectId if present to avoid jsonable_encoder errors
        if safe_settings.get("_id") is not None:
            try:
                safe_settings["_id"] = str(safe_settings["_id"])  # or just pop if not needed
            except Exception:
                safe_settings.pop("_id", None)
        if "providers" in safe_settings:
            for provider_id, provider_config in safe_settings["providers"].items():
                if "api_key" in provider_config:
                    # Replace with status indicator
                    provider_config["has_api_key"] = bool(provider_config["api_key"])
                    del provider_config["api_key"]
        
        return {"settings": safe_settings}
    except Exception as e:
        logger.error(f"Error getting user settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
