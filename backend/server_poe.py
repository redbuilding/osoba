"""
Poe MCP Server

Provides tools for listing Poe models and running text/image/video/audio
generation via the Poe OpenAI-compatible API.
"""
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv, find_dotenv
from fastmcp import FastMCP

# ---- Logging setup (stderr, same pattern as other MCP servers) ----
script_logger = logging.getLogger("server_poe")
script_logger.setLevel(logging.INFO)
if not script_logger.hasHandlers():
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - [SERVER_POE] %(message)s")
    )
    script_logger.addHandler(_handler)
    script_logger.propagate = False

# ---- Environment ----
dotenv_path = find_dotenv(usecwd=False, raise_error_if_not_found=False)
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

POE_API_KEY = os.getenv("POE_API_KEY")
if not POE_API_KEY:
    script_logger.critical("POE_API_KEY environment variable is not set.")
    raise ValueError("POE_API_KEY environment variable not set. Add it to your .env file.")

script_logger.info("POE_API_KEY loaded successfully.")

# ---- FastMCP server ----
mcp = FastMCP(
    name="PoeServer",
    version="0.1.0",
    instructions=(
        "Provides access to Poe AI models via the OpenAI-compatible API. "
        "Supports text chat and media generation (image, video, audio) using "
        "any model available on the Poe platform."
    ),
)

script_logger.info("FastMCP PoeServer instance created.")

# Import after env is loaded so POE_BASE_URL override is respected
from utils.poe_client import (  # noqa: E402
    PoeAPIError,
    PoeClient,
    POE_ALLOWED_MEDIA_HOSTS,
    POE_MAX_DOWNLOAD_BYTES,
    extract_urls,
    is_allowed_host,
)


def _make_client() -> PoeClient:
    return PoeClient(api_key=POE_API_KEY)


def _build_messages(
    prompt: str,
    system: Optional[str] = None,
    image_urls: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Build an OpenAI-compatible messages list."""
    messages: List[Dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    if image_urls:
        content_blocks: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
        for url in image_urls:
            content_blocks.append({"type": "image_url", "image_url": {"url": url}})
        messages.append({"role": "user", "content": content_blocks})
    else:
        messages.append({"role": "user", "content": prompt})
    return messages


def _extract_text(resp: Dict[str, Any]) -> str:
    """Pull the assistant text out of a chat/completions response."""
    choices = resp.get("choices") or []
    if not choices:
        return str(resp)
    msg = choices[0].get("message") or {}
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    return str(content)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def poe_list_models(
    input_modality: Optional[str] = None,
    output_modality: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """
    List available models on the Poe platform.

    Use the modality filters to find image/video/audio generation models.

    Args:
        input_modality: Optional filter — only return models that accept this
            input type. One of: text, image, video, audio
        output_modality: Optional filter — only return models that produce this
            output type. One of: text, image, video, audio
        search: Optional substring to search in model id or description
        limit: Maximum number of models to return (default 50, max 200)

    Returns:
        dict with count and models list (id, owned_by, description,
        input_modalities, output_modalities, pricing)
    """
    if limit < 1 or limit > 200:
        return {"status": "error", "message": "limit must be between 1 and 200"}

    VALID_MODALITIES = {"text", "image", "video", "audio"}
    if input_modality and input_modality not in VALID_MODALITIES:
        return {"status": "error", "message": f"Invalid input_modality '{input_modality}'. Valid: {sorted(VALID_MODALITIES)}"}
    if output_modality and output_modality not in VALID_MODALITIES:
        return {"status": "error", "message": f"Invalid output_modality '{output_modality}'. Valid: {sorted(VALID_MODALITIES)}"}

    try:
        async with _make_client() as client:
            result = await client.list_models(
                input_modality=input_modality,
                output_modality=output_modality,
                search=search,
                limit=limit,
            )
            script_logger.info(f"Listed {result['count']} Poe models")
            return {"status": "success", **result}
    except PoeAPIError as e:
        script_logger.error(f"Poe API error in poe_list_models: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in poe_list_models: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def poe_chat(
    prompt: str,
    model: str = "Claude-Sonnet-4-5",
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    image_urls: Optional[List[str]] = None,
) -> dict:
    """
    Send a chat message to a Poe model and get a text response.

    Use poe_list_models to discover available model IDs.

    Args:
        prompt: The user message to send
        model: Poe model ID (default: Claude-Sonnet-4-5). Use poe_list_models to browse.
        system: Optional system prompt to prepend
        temperature: Sampling temperature 0-2 (optional)
        max_tokens: Maximum tokens to generate (optional)
        image_urls: Optional list of image URLs to include as visual input
            (only supported by vision-capable models)

    Returns:
        dict with status, model, and text (the assistant's reply)
    """
    if not prompt:
        return {"status": "error", "message": "prompt is required"}
    if temperature is not None and not (0 <= temperature <= 2):
        return {"status": "error", "message": "temperature must be between 0 and 2"}
    if max_tokens is not None and max_tokens < 1:
        return {"status": "error", "message": "max_tokens must be at least 1"}

    try:
        messages = _build_messages(prompt, system=system, image_urls=image_urls)
        async with _make_client() as client:
            resp = await client.chat_completions(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        text = _extract_text(resp)
        script_logger.info(f"poe_chat completed: model={model}, chars={len(text)}")
        return {"status": "success", "model": model, "text": text}
    except PoeAPIError as e:
        script_logger.error(f"Poe API error in poe_chat: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in poe_chat: {e}")
        return {"status": "error", "message": str(e)}


async def _generate_media(
    *,
    prompt: str,
    model: str,
    system: Optional[str],
    temperature: Optional[float],
    max_tokens: Optional[int],
    download_media: bool,
    max_download_bytes: int,
) -> dict:
    """Shared implementation for the three generate_* tools."""
    messages = _build_messages(prompt, system=system)
    async with _make_client() as client:
        resp = await client.chat_completions(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        text = _extract_text(resp)
        urls = extract_urls(text)
        downloaded: List[Dict[str, Any]] = []

        if download_media and urls:
            for url in urls:
                if not is_allowed_host(url, POE_ALLOWED_MEDIA_HOSTS):
                    script_logger.debug(f"Skipping non-allowed host: {url}")
                    continue
                try:
                    media = await client.download_media(url, max_bytes=max_download_bytes)
                    downloaded.append(media)
                    script_logger.info(f"Downloaded {media['kind']} from {url} ({media['bytes']} bytes)")
                except Exception as dl_err:
                    downloaded.append({"url": url, "error": str(dl_err)})
                    script_logger.warning(f"Failed to download {url}: {dl_err}")

    return {
        "status": "success",
        "model": model,
        "raw_text": text,
        "extracted_urls": urls,
        "downloaded": downloaded,
    }


@mcp.tool()
async def poe_generate_image(
    prompt: str,
    model: str = "gpt-image-1.5",
    system: Optional[str] = None,
    download_media: bool = True,
    max_download_bytes: int = POE_MAX_DOWNLOAD_BYTES,
) -> dict:
    """
    Generate an image using a Poe image model.

    The model returns a response that typically contains image URLs. When
    download_media is True, Poe-hosted images are downloaded and returned
    as base64-encoded data in the 'downloaded' list.

    Use poe_list_models(output_modality='image') to discover image models.

    Args:
        prompt: Image generation prompt
        model: Poe image model ID (default: gpt-image-1.5)
        system: Optional system prompt
        download_media: If True, download Poe-hosted image URLs and include
            base64 data inline (default: True)
        max_download_bytes: Maximum bytes to download per image (default: 25MB)

    Returns:
        dict with status, model, raw_text, extracted_urls, downloaded
        Each downloaded item contains: url, content_type, bytes, kind, format, data_b64
    """
    if not prompt:
        return {"status": "error", "message": "prompt is required"}
    try:
        return await _generate_media(
            prompt=prompt,
            model=model,
            system=system,
            temperature=None,
            max_tokens=None,
            download_media=download_media,
            max_download_bytes=max_download_bytes,
        )
    except PoeAPIError as e:
        script_logger.error(f"Poe API error in poe_generate_image: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in poe_generate_image: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def poe_generate_video(
    prompt: str,
    model: str,
    system: Optional[str] = None,
    download_media: bool = False,
    max_download_bytes: int = POE_MAX_DOWNLOAD_BYTES,
) -> dict:
    """
    Generate a video using a Poe video model.

    The model returns a response that typically contains video URLs.
    Download is disabled by default (videos can be large — enable explicitly).

    Use poe_list_models(output_modality='video') to discover video models.

    Args:
        prompt: Video generation prompt
        model: Poe video model ID (required — use poe_list_models to find one)
        system: Optional system prompt
        download_media: If True, download Poe-hosted video URLs and include
            base64 data inline (default: False — videos can be large)
        max_download_bytes: Maximum bytes to download per video (default: 25MB)

    Returns:
        dict with status, model, raw_text, extracted_urls, downloaded
    """
    if not prompt:
        return {"status": "error", "message": "prompt is required"}
    if not model:
        return {"status": "error", "message": "model is required — use poe_list_models(output_modality='video') to find one"}
    try:
        return await _generate_media(
            prompt=prompt,
            model=model,
            system=system,
            temperature=None,
            max_tokens=None,
            download_media=download_media,
            max_download_bytes=max_download_bytes,
        )
    except PoeAPIError as e:
        script_logger.error(f"Poe API error in poe_generate_video: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in poe_generate_video: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def poe_generate_audio(
    prompt: str,
    model: str,
    system: Optional[str] = None,
    download_media: bool = False,
    max_download_bytes: int = POE_MAX_DOWNLOAD_BYTES,
) -> dict:
    """
    Generate audio using a Poe audio model (TTS, music, voice).

    The model returns a response that typically contains audio URLs.
    Download is disabled by default — enable explicitly when needed.

    Use poe_list_models(output_modality='audio') to discover audio models.

    Args:
        prompt: Audio generation prompt (voice description, music style, TTS text, etc.)
        model: Poe audio model ID (required — use poe_list_models to find one)
        system: Optional system prompt
        download_media: If True, download Poe-hosted audio URLs and include
            base64 data inline (default: False)
        max_download_bytes: Maximum bytes to download per audio file (default: 25MB)

    Returns:
        dict with status, model, raw_text, extracted_urls, downloaded
    """
    if not prompt:
        return {"status": "error", "message": "prompt is required"}
    if not model:
        return {"status": "error", "message": "model is required — use poe_list_models(output_modality='audio') to find one"}
    try:
        return await _generate_media(
            prompt=prompt,
            model=model,
            system=system,
            temperature=None,
            max_tokens=None,
            download_media=download_media,
            max_download_bytes=max_download_bytes,
        )
    except PoeAPIError as e:
        script_logger.error(f"Poe API error in poe_generate_audio: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in poe_generate_audio: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
