"""
Async HTTP client for the Poe API (OpenAI-compatible).

Handles model listing, text chat, and media generation via chat completions.
Supports optional media download with base64 encoding for inline delivery.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("poe_client")

POE_BASE_URL = os.getenv("POE_BASE_URL", "https://api.poe.com")
POE_MAX_DOWNLOAD_BYTES = int(os.getenv("POE_MAX_DOWNLOAD_BYTES", str(25 * 1024 * 1024)))  # 25 MB
POE_ALLOWED_MEDIA_HOSTS = tuple(
    h.strip() for h in os.getenv("POE_ALLOWED_MEDIA_HOSTS", "poe.com").split(",") if h.strip()
)

_URL_RE = re.compile(r"https?://[^\s)>\]]+")
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\((https?://[^)]+)\)")
_MD_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PoeAPIError(Exception):
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        response_data: Optional[Dict] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.response_data = response_data or {}
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ModelInfo(BaseModel):
    id: str
    owned_by: Optional[str] = None
    description: Optional[str] = None
    input_modalities: Optional[List[str]] = None
    output_modalities: Optional[List[str]] = None
    pricing: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    role: str  # system | user | assistant
    content: Any  # str or content-block list (OpenAI-compatible)
    name: Optional[str] = None


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def extract_urls(text: str) -> List[str]:
    """Extract all HTTP(S) URLs from a block of text, including markdown links."""
    urls: set[str] = set(_URL_RE.findall(text or ""))
    urls.update(_MD_IMAGE_RE.findall(text or ""))
    urls.update(_MD_LINK_RE.findall(text or ""))
    return sorted(urls)


def is_allowed_host(url: str, allowed_hosts: tuple) -> bool:
    """Return True if the URL hostname matches one of the allowed host suffixes."""
    try:
        host = httpx.URL(url).host or ""
    except Exception:
        return False
    host = host.lower()
    return any(host == h.lower() or host.endswith("." + h.lower()) for h in allowed_hosts)


def guess_media_kind(content_type: Optional[str]) -> str:
    """Map a MIME type to a simple kind label: image | audio | video | file."""
    if not content_type:
        return "file"
    ct = content_type.split(";")[0].strip().lower()
    if ct.startswith("image/"):
        return "image"
    if ct.startswith("audio/"):
        return "audio"
    if ct.startswith("video/"):
        return "video"
    return "file"


def guess_ext(content_type: Optional[str]) -> str:
    """Best-effort file extension from a MIME type."""
    if not content_type:
        return "bin"
    ct = content_type.split(";")[0].strip().lower()
    ext = mimetypes.guess_extension(ct)
    if ext:
        return ext.lstrip(".")
    if ct == "image/jpg":
        return "jpg"
    return "bin"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class PoeClient:
    """Async client for the Poe OpenAI-compatible API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._base_headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _handle_error(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                error_data = e.response.json()
            except Exception:
                error_data = {}
            # Poe wraps errors in {"error": {"code": ..., "message": ...}} or {"error": "..."}
            err_field = error_data.get("error", {})
            if isinstance(err_field, dict):
                error_code = str(err_field.get("code", "POE_API_ERROR"))
                message = err_field.get("message", str(e))
            else:
                error_code = str(err_field) if err_field else "POE_API_ERROR"
                message = str(e)
            logger.error(f"Poe API HTTP error {status_code}: {message}")
            raise PoeAPIError(
                message=message,
                status_code=status_code,
                error_code=error_code,
                response_data=error_data,
            )

    async def list_models(
        self,
        input_modality: Optional[str] = None,
        output_modality: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List available Poe models, optionally filtered by modality or name."""
        timeout = httpx.Timeout(60.0, connect=15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(
                f"{POE_BASE_URL}/v1/models",
                headers=self._base_headers,
            )
            await self._handle_error(r)
            data = r.json()

        models = data.get("data", [])
        filtered = []
        for m in models:
            arch = m.get("architecture") or {}
            in_mods = set(arch.get("input_modalities") or [])
            out_mods = set(arch.get("output_modalities") or [])
            if input_modality and input_modality not in in_mods:
                continue
            if output_modality and output_modality not in out_mods:
                continue
            if search:
                haystack = (m.get("id", "") + " " + (m.get("description") or "")).lower()
                if search.lower() not in haystack:
                    continue
            filtered.append(m)
            if len(filtered) >= limit:
                break

        return {
            "count": len(filtered),
            "models": [
                ModelInfo(
                    id=m.get("id", ""),
                    owned_by=m.get("owned_by"),
                    description=m.get("description"),
                    input_modalities=(m.get("architecture") or {}).get("input_modalities"),
                    output_modalities=(m.get("architecture") or {}).get("output_modalities"),
                    pricing=m.get("pricing"),
                ).model_dump()
                for m in filtered
            ],
        }

    async def chat_completions(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Call Poe chat/completions. Returns the full API response dict."""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        timeout = httpx.Timeout(120.0, connect=15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                f"{POE_BASE_URL}/v1/chat/completions",
                headers=self._base_headers,
                json=payload,
            )
            await self._handle_error(r)
            return r.json()

    async def download_media(
        self,
        url: str,
        max_bytes: int = POE_MAX_DOWNLOAD_BYTES,
    ) -> Dict[str, Any]:
        """
        Stream-download a media URL and return base64-encoded data with metadata.

        Returns a dict with: url, content_type, bytes, kind, format, data_b64
        Raises PoeAPIError if the download exceeds max_bytes.
        """
        timeout = httpx.Timeout(60.0, connect=15.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", url) as r:
                r.raise_for_status()
                content_type = r.headers.get("content-type")
                total = 0
                chunks: List[bytes] = []
                async for chunk in r.aiter_bytes():
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        raise PoeAPIError(
                            f"Media download exceeds limit ({max_bytes} bytes). "
                            "Increase POE_MAX_DOWNLOAD_BYTES to allow larger files.",
                            error_code="DOWNLOAD_TOO_LARGE",
                        )
                    chunks.append(chunk)
                data = b"".join(chunks)

        ct = (content_type or "").split(";")[0].strip().lower()
        return {
            "url": url,
            "content_type": ct,
            "bytes": total,
            "kind": guess_media_kind(ct),
            "format": guess_ext(ct),
            "data_b64": base64.b64encode(data).decode("utf-8"),
        }

    async def close(self) -> None:
        pass  # Stateless client — no persistent connection to clean up

    async def __aenter__(self) -> "PoeClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
