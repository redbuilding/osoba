import asyncio
import json
import os
from typing import Optional, List, Dict, AsyncGenerator

import litellm
import ollama
from openai import APITimeoutError, BadRequestError, AuthenticationError, NotFoundError, RateLimitError, APIConnectionError, InternalServerError
from fastapi import HTTPException

from core.config import DEFAULT_MODEL, DEFAULT_REPEAT_PENALTY, OLLAMA_API_BASE, get_logger
from services.provider_service import (
    chat_with_provider, stream_chat_with_provider, get_available_models_by_provider,
    get_provider_status, validate_provider_api_key
)
from core.providers import PROVIDER_CONFIGS

logger = get_logger("llm_service")

def _has_known_provider_prefix(model_name: str) -> bool:
    try:
        for cfg in PROVIDER_CONFIGS.values():
            prefix = cfg.get("model_prefix", "")
            if prefix and model_name.startswith(prefix):
                return True
    except Exception:
        pass
    return False

# Backward compatibility functions - delegate to provider_service
async def chat_with_ollama(messages: List[Dict[str, str]], model_name: str,
                          repeat_penalty: float = DEFAULT_REPEAT_PENALTY) -> Optional[str]:
    """Backward compatibility wrapper: if model_name already includes a provider prefix, use as-is; else assume Ollama."""
    full_model_name = model_name if _has_known_provider_prefix(model_name) else (
        f"ollama/{model_name}" if not model_name.startswith("ollama/") else model_name
    )
    return await chat_with_provider(messages, full_model_name, repeat_penalty)

async def stream_chat_with_ollama(messages: List[Dict[str, str]], model_name: str, 
                                 repeat_penalty: float = DEFAULT_REPEAT_PENALTY) -> AsyncGenerator[str, None]:
    """Backward compatibility wrapper: respect existing provider prefix; otherwise default to Ollama."""
    full_model_name = model_name if _has_known_provider_prefix(model_name) else (
        f"ollama/{model_name}" if not model_name.startswith("ollama/") else model_name
    )
    async for chunk in stream_chat_with_provider(messages, full_model_name, repeat_penalty):
        yield chunk

async def get_default_ollama_model() -> str:
    """Get default Ollama model for backward compatibility."""
    try:
        models_by_provider = await get_available_models_by_provider()
        ollama_models = models_by_provider.get('ollama', [])
        
        if ollama_models:
            # Prefer models with "instruct" or "chat" in name
            preferred = [m for m in ollama_models if any(keyword in m.lower() for keyword in ['instruct', 'chat'])]
            if preferred:
                return preferred[0]
            return ollama_models[0]
    except Exception as e:
        logger.warning(f"Could not get Ollama models: {e}")
    
    return DEFAULT_MODEL.replace('ollama/', '') if DEFAULT_MODEL.startswith('ollama/') else DEFAULT_MODEL

async def list_ollama_models_info() -> List[Dict]:
    """Get Ollama model info for backward compatibility."""
    try:
        response = await asyncio.to_thread(ollama.list)
        if response and isinstance(response.get('models'), list):
            return response['models']
        return []
    except BadRequestError as e:
        logger.error(f"LLM API BadRequestError: {e.status_code} - {e}", exc_info=True)
        raise HTTPException(status_code=e.status_code or 400, detail=f"LLM API error: {e}")
    except APIConnectionError as e:
        host = os.getenv('OLLAMA_HOST','localhost:11434')
        actual_host = f"http://{host}" if not host.startswith(('http://','https://')) else host
        logger.error(f"LLM API ConnectionError (could not connect to {actual_host}): {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Could not connect to LLM service at {actual_host}. Ensure Ollama is running.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching LLM models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching LLM models.")

async def get_ollama_model_tags() -> List[str]:
    """Get Ollama model tags for backward compatibility."""
    try:
        models_by_provider = await get_available_models_by_provider()
        ollama_models = models_by_provider.get('ollama', [])
        return sorted(ollama_models)
    except Exception as e:
        logger.error(f"Error getting Ollama model tags: {e}")
        return []
