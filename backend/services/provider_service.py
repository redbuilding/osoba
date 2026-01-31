import asyncio
import json
import os
from typing import Optional, List, Dict, AsyncGenerator, Any

import litellm
import ollama
from openai import APITimeoutError, BadRequestError, AuthenticationError, NotFoundError, RateLimitError, APIConnectionError, InternalServerError
from fastapi import HTTPException

from core.config import DEFAULT_MODEL, DEFAULT_REPEAT_PENALTY, OLLAMA_API_BASE, get_logger
from core.providers import (
    PROVIDER_CONFIGS, get_provider_config, get_available_providers, 
    is_provider_configured, get_model_with_prefix, extract_provider_from_model
)
from db.settings_crud import get_provider_api_key, encrypt_api_key, decrypt_api_key

logger = get_logger("provider_service")

async def chat_with_provider(messages: List[Dict[str, str]], model_name: str, 
                           repeat_penalty: float = DEFAULT_REPEAT_PENALTY,
                           user_id: str = "default") -> Optional[str]:
    """
    Chat completion using any configured provider.
    """
    try:
        valid_messages = [msg for msg in messages if isinstance(msg, dict) and 'role' in msg and 'content' in msg]
        if not valid_messages:
            logger.error(f"[LLM] No valid messages provided to model '{model_name}'.")
            return None

        # Extract provider and configure request
        provider_id, clean_model = extract_provider_from_model(model_name)
        config = get_provider_config(provider_id)
        
        if not config:
            logger.error(f"[LLM] Unknown provider for model '{model_name}'")
            return None

        # Build request parameters with correct provider prefix
        full_model = get_model_with_prefix(provider_id, clean_model)
        request_params = {
            "model": full_model,
            "messages": valid_messages,
            "temperature": 1.0 / repeat_penalty if repeat_penalty > 0 else 1.0
        }

        # Add provider-specific parameters
        await _add_provider_params(request_params, provider_id, config, user_id)

        logger.info(f"[LLM] Making request to provider '{provider_id}' with model '{model_name}', params: {list(request_params.keys())}")
        response = await litellm.acompletion(**request_params)
        
        if response and response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
        
        logger.warning(f"[LLM] Unexpected response structure from model '{model_name}': {response}")
        return None
        
    except Exception as e:
        logger.error(f"[LLM] Error with model '{model_name}': {e}", exc_info=True)
        return None

async def stream_chat_with_provider(messages: List[Dict[str, str]], model_name: str, 
                                  repeat_penalty: float = DEFAULT_REPEAT_PENALTY,
                                  user_id: str = "default") -> AsyncGenerator[str, None]:
    """
    Streaming chat completion using any configured provider.
    """
    try:
        valid_messages = [msg for msg in messages if isinstance(msg, dict) and 'role' in msg and 'content' in msg]
        if not valid_messages:
            logger.error(f"[LLM] No valid messages provided to model '{model_name}'.")
            return

        # Extract provider and configure request
        provider_id, clean_model = extract_provider_from_model(model_name)
        config = get_provider_config(provider_id)
        
        if not config:
            logger.error(f"[LLM] Unknown provider for model '{model_name}'")
            return

        # Build request parameters with correct provider prefix
        full_model = get_model_with_prefix(provider_id, clean_model)
        request_params = {
            "model": full_model,
            "messages": valid_messages,
            "stream": True,
            "temperature": 1.0 / repeat_penalty if repeat_penalty > 0 else 1.0
        }

        # Add provider-specific parameters
        await _add_provider_params(request_params, provider_id, config, user_id)

        logger.info(f"[LLMStream] Making streaming request to provider '{provider_id}' with model '{model_name}', params: {list(request_params.keys())}")
        response = await litellm.acompletion(**request_params)

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                logger.debug(f"[LLMStream] Raw token: {repr(token)}")
                payload = json.dumps({"type": "token", "content": token})
                yield f"data: {payload}\n\n"
                
    except Exception as e:
        logger.error(f"[LLMStream] Error with model '{model_name}': {e}", exc_info=True)
        err_payload = json.dumps(
            {'type': 'error', 'content': f"LLM stream error: {str(e)}"}
        )
        yield f"data: {err_payload}\n\n"

async def _add_provider_params(request_params: Dict[str, Any], provider_id: str, 
                             config: Dict[str, Any], user_id: str = "default"):
    """Add provider-specific parameters to the request."""
    
    # Add API key if required
    if config.get('api_key_env') and provider_id != 'ollama':
        api_key = get_provider_api_key(provider_id, user_id)
        if not api_key:
            # Fallback to environment variable
            api_key = os.getenv(config['api_key_env'])
        if api_key:
            # Explicitly pass API key to LiteLLM to avoid relying on global env state
            request_params['api_key'] = api_key
            # Also set env var for any internal library lookups
            os.environ[config['api_key_env']] = api_key
        else:
            raise ValueError(f"No API key configured for provider {provider_id}")
    
    # Add API base if configured
    if provider_id == 'ollama':
        request_params['api_base'] = config.get('default_api_base', OLLAMA_API_BASE)
    elif config.get('api_base_env'):
        api_base = os.getenv(config['api_base_env'])
        if api_base:
            request_params['api_base'] = api_base
    # For other providers like OpenRouter, don't set api_base - let LiteLLM use defaults
    
    # Provider-specific headers (optional but recommended)
    if provider_id == 'openrouter':
        # OpenRouter recommends sending HTTP-Referer and X-Title for routing/attribution
        # These aren't required for auth but help with 401 cases behind proxies
        headers = request_params.get('extra_headers') or {}
        headers.setdefault('HTTP-Referer', os.getenv('OPENROUTER_HTTP_REFERER', 'http://localhost'))
        headers.setdefault('X-Title', os.getenv('OPENROUTER_APP_NAME', 'MCP App'))
        request_params['extra_headers'] = headers
    
    # Add max_tokens for Anthropic
    if config.get('requires_max_tokens'):
        request_params['max_tokens'] = config.get('default_max_tokens', 4096)

async def get_available_models_by_provider() -> Dict[str, List[str]]:
    """Get available models grouped by provider."""
    models_by_provider = {}
    
    for provider_id in get_available_providers():
        config = get_provider_config(provider_id)
        if not config:
            continue
            
        try:
            if provider_id == 'ollama':
                # Get actual Ollama models
                models = await _get_ollama_models()
                models_by_provider[provider_id] = models
            else:
                # For other providers, use default models from config
                # In a real implementation, you might query their APIs for available models
                models = config.get('default_models', [])
                models_by_provider[provider_id] = models
                
        except Exception as e:
            logger.warning(f"Could not get models for provider {provider_id}: {e}")
            models_by_provider[provider_id] = []
    
    return models_by_provider

async def _get_ollama_models() -> List[str]:
    """Get available Ollama models."""
    try:
        response = await asyncio.to_thread(ollama.list)
        if response and isinstance(response.get('models'), list):
            models = [m['model'] for m in response['models'] if m.get('model')]
            # Filter out embedding models
            non_embed_models = [
                m for m in models
                if 'embed' not in m.lower()
            ]
            return sorted(non_embed_models)
        return []
    except Exception as e:
        logger.error(f"Error getting Ollama models: {e}")
        return []

async def get_provider_status(provider_id: str, user_id: str = "default") -> Dict[str, Any]:
    """Get status information for a provider."""
    config = get_provider_config(provider_id)
    if not config:
        return {"provider_id": provider_id, "available": False, "error": "Unknown provider"}
    
    status = {
        "provider_id": provider_id,
        "name": config["name"],
        "available": False,
        "configured": False,
        "requires_api_key": bool(config.get('api_key_env')),
        "supports_streaming": config.get('supports_streaming', False)
    }
    
    try:
        # Check if provider is configured
        if provider_id == 'ollama':
            # For Ollama, check if service is running
            models = await _get_ollama_models()
            status["configured"] = True
            status["available"] = len(models) > 0
            status["model_count"] = len(models)
        else:
            # For other providers, check if API key is available
            api_key = get_provider_api_key(provider_id, user_id)
            if not api_key:
                api_key = os.getenv(config.get('api_key_env', ''))
            
            status["configured"] = bool(api_key)
            status["available"] = bool(api_key)  # Assume available if configured
            
    except Exception as e:
        status["error"] = str(e)
        logger.error(f"Error checking provider {provider_id} status: {e}")
    
    return status

async def validate_provider_api_key(provider_id: str, api_key: str) -> Dict[str, Any]:
    """Validate an API key for a provider by making a test request."""
    config = get_provider_config(provider_id)
    if not config:
        return {"valid": False, "error": "Unknown provider"}
    
    if provider_id == 'ollama':
        return {"valid": True, "message": "Ollama doesn't require API key validation"}
    
    try:
        # Temporarily set the API key
        old_key = os.environ.get(config['api_key_env']) if config.get('api_key_env') else None
        if config.get('api_key_env'):
            os.environ[config['api_key_env']] = api_key
        
        # Make a simple test request
        health_check_model = config.get('health_check_model')
        if not health_check_model:
            return {"valid": True, "message": "No health check model configured"}
        
        test_messages = [{"role": "user", "content": "Hi"}]
        # Ensure provider-prefixed model for health check
        provider_id = provider_id
        from core.providers import get_model_with_prefix
        request_params = {
            "model": get_model_with_prefix(provider_id, health_check_model),
            "messages": test_messages,
            "max_tokens": 1
        }
        # Explicitly pass API key to LiteLLM to avoid reliance on env
        if provider_id != 'ollama' and config.get('api_key_env'):
            request_params['api_key'] = api_key
        
        # Add provider-specific params
        if config.get('requires_max_tokens'):
            request_params['max_tokens'] = 1
        
        response = await litellm.acompletion(**request_params)
        
        # Restore old key
        if config.get('api_key_env'):
            if old_key:
                os.environ[config['api_key_env']] = old_key
            elif config['api_key_env'] in os.environ:
                del os.environ[config['api_key_env']]
        
        return {"valid": True, "message": "API key validated successfully"}
        
    except AuthenticationError:
        return {"valid": False, "error": "Invalid API key"}
    except Exception as e:
        return {"valid": False, "error": f"Validation failed: {str(e)}"}
    finally:
        # Ensure we restore the environment
        if config.get('api_key_env'):
            if old_key:
                os.environ[config['api_key_env']] = old_key
            elif config['api_key_env'] in os.environ:
                del os.environ[config['api_key_env']]

# Backward compatibility functions
from core.providers import PROVIDER_CONFIGS

def _has_known_provider_prefix(model_name: str) -> bool:
    try:
        for cfg in PROVIDER_CONFIGS.values():
            prefix = cfg.get("model_prefix", "")
            if prefix and model_name.startswith(prefix):
                return True
    except Exception:
        pass
    return False

async def chat_with_ollama(messages: List[Dict[str, str]], model_name: str,
                          repeat_penalty: float = DEFAULT_REPEAT_PENALTY) -> Optional[str]:
    """Backward compatibility wrapper: if model already has a provider prefix, use it; otherwise assume Ollama."""
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
        models = await _get_ollama_models()
        if models:
            # Prefer models with "instruct" or "chat" in name
            preferred = [m for m in models if any(keyword in m.lower() for keyword in ['instruct', 'chat'])]
            if preferred:
                return preferred[0]
            return models[0]
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
    except Exception as e:
        logger.error(f"Error getting Ollama model info: {e}")
        return []

async def get_ollama_model_tags() -> List[str]:
    """Get Ollama model tags for backward compatibility."""
    models = await _get_ollama_models()
    return models
