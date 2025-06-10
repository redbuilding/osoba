import asyncio
import json
import os
from typing import Optional, List, Dict, AsyncGenerator

import ollama
from fastapi import HTTPException

from core.config import DEFAULT_OLLAMA_MODEL, DEFAULT_REPEAT_PENALTY, get_logger

logger = get_logger("ollama_service")

async def chat_with_ollama(messages: List[Dict[str, str]], model_name: str,
                            repeat_penalty: float = DEFAULT_REPEAT_PENALTY) -> Optional[str]:
    try:
        valid_messages = [msg for msg in messages if isinstance(msg, dict) and 'role' in msg and 'content' in msg]
        if not valid_messages:
            logger.error(f"[Ollama] No valid messages provided to model '{model_name}'.")
            return None

        response = await asyncio.to_thread(
            ollama.chat,
            model=model_name,
            messages=valid_messages,
            options={"repeat_penalty": repeat_penalty}
        )
        if response and "message" in response and "content" in response["message"]:
            return response["message"]["content"]
        logger.warning(f"[Ollama] Unexpected response structure from model '{model_name}': {response}")
        return None
    except Exception as e:
        logger.error(f"[Ollama] Error with model '{model_name}': {e}", exc_info=True)
        return None

async def stream_chat_with_ollama(messages: List[Dict[str, str]], model_name: str, repeat_penalty: float = DEFAULT_REPEAT_PENALTY) -> AsyncGenerator[str, None]:
    """
    Async generator that yields Server-Sent Event (SSE) lines containing tokens
    streamed from Ollama.
    """
    try:
        stream_iter = await asyncio.to_thread(
            ollama.chat,
            model=model_name,
            messages=messages,
            stream=True,
            options={"repeat_penalty": repeat_penalty}
        )

        for chunk in stream_iter:
            if chunk and "message" in chunk and "content" in chunk["message"]:
                token = chunk["message"]["content"]
                payload = json.dumps({"type": "token", "content": token})
                yield f"data: {payload}\n\n"
    except Exception as e:
        logger.error(f"[OllamaStream] Error with model '{model_name}': {e}", exc_info=True)
        err_payload = json.dumps(
            {'type': 'error', 'content': f"Ollama stream error: {str(e)}"}
        )
        yield f"data: {err_payload}\n\n"

async def get_default_ollama_model() -> str:
    try:
        models_info = await list_ollama_models_info()
        non_embed_models = [
            m['model'] for m in models_info
            if 'embed' not in m.get('details', {}).get('family', '').lower()
            and 'embed' not in m['model'].lower()
        ]
        if non_embed_models:
            return non_embed_models[0]
        if models_info:
            return models_info[0]['model']
    except Exception as e:
        logger.warning(f"Could not get Ollama models due to an error: {e}. Falling back to default.", exc_info=False)
    return DEFAULT_OLLAMA_MODEL

async def list_ollama_models_info() -> List[Dict]:
    """Internal function to fetch raw model data."""
    try:
        response = await asyncio.to_thread(ollama.list)
        if response and isinstance(response.get('models'), list):
            return response['models']
        logger.warning(f"Unexpected format from ollama.list(): {response}. Expected .models list.")
        return []
    except ollama.ResponseError as e:
        logger.error(f"Ollama API ResponseError: {e.status_code} - {e.error}", exc_info=True)
        raise HTTPException(status_code=e.status_code or 500, detail=f"Ollama API error: {e.error or 'Unknown Ollama API response error'}")
    except ollama.RequestError as e:
        host = os.getenv('OLLAMA_HOST','localhost:11434')
        actual_host = f"http://{host}" if not host.startswith(('http://','https://')) else host
        logger.error(f"Ollama API RequestError (could not connect to {actual_host}): {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Could not connect to Ollama service at {actual_host}. Ensure Ollama is running.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching Ollama models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching Ollama models.")

async def get_ollama_model_tags() -> List[str]:
    """Fetches just the model tags for API responses."""
    models_info = await list_ollama_models_info()
    tags = [m['model'] for m in models_info if m.get('model')]
    if not tags and models_info:
        logger.warning("ollama.list() returned models, but no valid model tags found after filtering.")
    return sorted(list(set(tags)))
