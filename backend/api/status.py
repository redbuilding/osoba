from typing import List
from fastapi import APIRouter, HTTPException
import ollama

from services.mcp_service import app_state
from db.mongodb import conversations_collection, tasks_collection
from services.llm_service import get_ollama_model_tags, list_ollama_models_info
from services.provider_service import get_available_models_by_provider, get_provider_status

router = APIRouter()

@router.get("/api/status")
async def get_status():
    """Provides the operational status of backend services."""
    ollama_ok = False
    try:
        # A lightweight check
        await list_ollama_models_info()
        ollama_ok = True
    except HTTPException:
        ollama_ok = False # Raised by service on connection error
    except Exception:
        ollama_ok = False

    status_payload = {
        "db_connected": conversations_collection is not None,
        "ollama_available": ollama_ok,
        "mcp_services": {},
        "tasks": {"active": 0}
    }
    # Count active tasks if tasks collection is available
    try:
        if tasks_collection is not None:
            active = tasks_collection.count_documents({"status": {"$in": ["PLANNING", "PENDING", "RUNNING"]}})
            status_payload["tasks"]["active"] = int(active)
    except Exception:
        pass
    for name, config in app_state.mcp_configs.items():
        status_payload["mcp_services"][name] = {
            "ready": app_state.mcp_service_ready.get(name, False),
            "enabled": config.enabled
        }
    return status_payload

@router.get("/api/ollama-models", response_model=List[str])
async def list_ollama_models_endpoint():
    """Lists available LLM model tags (backward compatibility)."""
    # The service function already handles exceptions and converts them to HTTPException
    return await get_ollama_model_tags()

@router.get("/api/models")
async def list_all_models_endpoint():
    """Lists available models from all providers with provider information."""
    try:
        models_by_provider = await get_available_models_by_provider()
        
        # Format for backward compatibility and enhanced information
        all_models = []
        provider_info = {}
        
        for provider_id, models in models_by_provider.items():
            status = await get_provider_status(provider_id)
            provider_info[provider_id] = status
            
            for model in models:
                # Add provider prefix if not already present
                if provider_id == 'ollama':
                    model_name = model  # Keep ollama models without prefix for compatibility
                else:
                    model_name = f"{provider_id}/{model}" if not model.startswith(f"{provider_id}/") else model
                
                all_models.append({
                    "name": model_name,
                    "provider": provider_id,
                    "available": status.get("available", False)
                })
        
        return {
            "models": all_models,
            "providers": provider_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
