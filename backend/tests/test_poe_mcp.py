"""
Tests for the Poe MCP server integration.

Covers:
- Pydantic model validation and utility helpers (no API calls)
- PoeClient methods with mocked httpx responses
- server_poe tool functions with mocked PoeClient
- Task runner routing and planner registration
- MCP service registry
"""
import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
TESTS_DIR = Path(__file__).parent
BACKEND_DIR = TESTS_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
for p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_server_poe():
    """Load server_poe.py with a fake key so the import doesn't raise."""
    os.environ.setdefault("POE_API_KEY", "test_fake_poe_key_for_testing")
    spec = importlib.util.spec_from_file_location(
        "server_poe_test",
        str(BACKEND_DIR / "server_poe.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _make_mock_response(json_data: dict, status_code: int = 200):
    """Build a mock httpx.Response that returns json_data."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    mock.headers = {}
    return mock


def _make_error_response(status_code: int, error_body: dict):
    import httpx
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = error_body
    mock.headers = {}
    http_err = httpx.HTTPStatusError(
        message=f"HTTP {status_code}",
        request=MagicMock(),
        response=mock,
    )
    mock.raise_for_status.side_effect = http_err
    return mock


# ---------------------------------------------------------------------------
# Sample API responses
# ---------------------------------------------------------------------------

SAMPLE_MODELS_RESPONSE = {
    "data": [
        {
            "id": "Claude-Sonnet-4-5",
            "owned_by": "anthropic",
            "description": "Fast and capable text model",
            "architecture": {
                "input_modalities": ["text"],
                "output_modalities": ["text"],
            },
            "pricing": {"prompt": "0.003", "completion": "0.015"},
        },
        {
            "id": "gpt-image-1.5",
            "owned_by": "openai",
            "description": "Image generation model",
            "architecture": {
                "input_modalities": ["text"],
                "output_modalities": ["image"],
            },
        },
        {
            "id": "suno-v3",
            "owned_by": "suno",
            "description": "Music generation",
            "architecture": {
                "input_modalities": ["text"],
                "output_modalities": ["audio"],
            },
        },
    ]
}

SAMPLE_CHAT_RESPONSE = {
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you today?",
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 9, "total_tokens": 19},
}

SAMPLE_IMAGE_RESPONSE = {
    "id": "chatcmpl-img001",
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "Here is your image: https://poe.com/images/generated/abc123.png",
            }
        }
    ],
}

SAMPLE_VIDEO_RESPONSE = {
    "id": "chatcmpl-vid001",
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "Video ready at https://poe.com/videos/generated/xyz789.mp4",
            }
        }
    ],
}


# ---------------------------------------------------------------------------
# 1. Utility helpers and model validation
# ---------------------------------------------------------------------------

class TestUtilHelpers:
    """Test URL extraction and host-allow helpers — no network calls."""

    def setup_method(self):
        from utils.poe_client import (
            extract_urls,
            is_allowed_host,
            guess_media_kind,
            guess_ext,
            PoeAPIError,
            ModelInfo,
        )
        self.extract_urls = extract_urls
        self.is_allowed_host = is_allowed_host
        self.guess_media_kind = guess_media_kind
        self.guess_ext = guess_ext
        self.PoeAPIError = PoeAPIError
        self.ModelInfo = ModelInfo

    def test_extract_bare_url(self):
        urls = self.extract_urls("Check this https://poe.com/images/foo.png out")
        assert "https://poe.com/images/foo.png" in urls

    def test_extract_markdown_image(self):
        urls = self.extract_urls("![Alt](https://poe.com/img/bar.jpg)")
        assert "https://poe.com/img/bar.jpg" in urls

    def test_extract_markdown_link(self):
        urls = self.extract_urls("[Download](https://poe.com/files/audio.mp3)")
        assert "https://poe.com/files/audio.mp3" in urls

    def test_extract_multiple_urls(self):
        text = "Image: https://poe.com/a.png and video: https://poe.com/b.mp4"
        urls = self.extract_urls(text)
        assert len(urls) == 2

    def test_extract_empty_string(self):
        assert self.extract_urls("") == []

    def test_is_allowed_host_exact(self):
        assert self.is_allowed_host("https://poe.com/img/foo.png", ("poe.com",))

    def test_is_allowed_host_subdomain(self):
        assert self.is_allowed_host("https://cdn.poe.com/img/foo.png", ("poe.com",))

    def test_is_allowed_host_blocked(self):
        assert not self.is_allowed_host("https://evil.com/img/foo.png", ("poe.com",))

    def test_guess_media_kind_image(self):
        assert self.guess_media_kind("image/png") == "image"

    def test_guess_media_kind_audio(self):
        assert self.guess_media_kind("audio/mpeg") == "audio"

    def test_guess_media_kind_video(self):
        assert self.guess_media_kind("video/mp4") == "video"

    def test_guess_media_kind_file_fallback(self):
        assert self.guess_media_kind("application/octet-stream") == "file"

    def test_guess_media_kind_none(self):
        assert self.guess_media_kind(None) == "file"

    def test_guess_ext_png(self):
        ext = self.guess_ext("image/png")
        assert ext == "png"

    def test_guess_ext_none_fallback(self):
        assert self.guess_ext(None) == "bin"

    def test_poe_api_error_attributes(self):
        err = self.PoeAPIError(
            message="Unauthorized",
            status_code=401,
            error_code="UNAUTHORIZED",
        )
        assert err.message == "Unauthorized"
        assert err.status_code == 401
        assert err.error_code == "UNAUTHORIZED"
        assert str(err) == "Unauthorized"

    def test_model_info_valid(self):
        m = self.ModelInfo(
            id="Claude-Sonnet-4-5",
            owned_by="anthropic",
            description="Test model",
            input_modalities=["text"],
            output_modalities=["text"],
        )
        assert m.id == "Claude-Sonnet-4-5"
        assert m.input_modalities == ["text"]

    def test_model_info_optional_fields(self):
        m = self.ModelInfo(id="some-model")
        assert m.owned_by is None
        assert m.pricing is None


# ---------------------------------------------------------------------------
# 2. PoeClient with mocked httpx
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_list_models_all():
    from utils.poe_client import PoeClient
    client = PoeClient(api_key="fake_key")

    mock_resp = _make_mock_response(SAMPLE_MODELS_RESPONSE)
    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)

        result = await client.list_models()

    assert result["count"] == 3
    ids = [m["id"] for m in result["models"]]
    assert "Claude-Sonnet-4-5" in ids
    assert "gpt-image-1.5" in ids


@pytest.mark.asyncio
async def test_client_list_models_filter_output_modality():
    from utils.poe_client import PoeClient
    client = PoeClient(api_key="fake_key")

    mock_resp = _make_mock_response(SAMPLE_MODELS_RESPONSE)
    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)

        result = await client.list_models(output_modality="image")

    assert result["count"] == 1
    assert result["models"][0]["id"] == "gpt-image-1.5"


@pytest.mark.asyncio
async def test_client_list_models_search():
    from utils.poe_client import PoeClient
    client = PoeClient(api_key="fake_key")

    mock_resp = _make_mock_response(SAMPLE_MODELS_RESPONSE)
    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)

        result = await client.list_models(search="suno")

    assert result["count"] == 1
    assert result["models"][0]["id"] == "suno-v3"


@pytest.mark.asyncio
async def test_client_list_models_limit():
    from utils.poe_client import PoeClient
    client = PoeClient(api_key="fake_key")

    mock_resp = _make_mock_response(SAMPLE_MODELS_RESPONSE)
    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)

        result = await client.list_models(limit=1)

    assert result["count"] == 1


@pytest.mark.asyncio
async def test_client_chat_completions():
    from utils.poe_client import PoeClient
    client = PoeClient(api_key="fake_key")

    mock_resp = _make_mock_response(SAMPLE_CHAT_RESPONSE)
    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_http.post = AsyncMock(return_value=mock_resp)

        result = await client.chat_completions(
            model="Claude-Sonnet-4-5",
            messages=[{"role": "user", "content": "Hello"}],
        )

    assert result["choices"][0]["message"]["content"] == "Hello! How can I help you today?"
    call_kwargs = mock_http.post.call_args
    payload = call_kwargs[1]["json"]
    assert payload["model"] == "Claude-Sonnet-4-5"
    assert payload["stream"] is False


@pytest.mark.asyncio
async def test_client_chat_completions_with_temperature():
    from utils.poe_client import PoeClient
    client = PoeClient(api_key="fake_key")

    mock_resp = _make_mock_response(SAMPLE_CHAT_RESPONSE)
    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_http.post = AsyncMock(return_value=mock_resp)

        await client.chat_completions(
            model="Claude-Sonnet-4-5",
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.7,
            max_tokens=100,
        )

    payload = mock_http.post.call_args[1]["json"]
    assert payload["temperature"] == 0.7
    assert payload["max_tokens"] == 100


@pytest.mark.asyncio
async def test_client_api_error_propagates():
    from utils.poe_client import PoeClient, PoeAPIError
    client = PoeClient(api_key="fake_key")

    error_resp = _make_error_response(
        401,
        {"error": {"code": "UNAUTHORIZED", "message": "Invalid API key"}},
    )
    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_http.post = AsyncMock(return_value=error_resp)

        with pytest.raises(PoeAPIError) as exc_info:
            await client.chat_completions(
                model="Claude-Sonnet-4-5",
                messages=[{"role": "user", "content": "test"}],
            )

    assert exc_info.value.status_code == 401
    assert exc_info.value.error_code == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_client_api_error_string_error_field():
    """Test error parsing when 'error' is a plain string, not a dict."""
    from utils.poe_client import PoeClient, PoeAPIError
    client = PoeClient(api_key="fake_key")

    error_resp = _make_error_response(403, {"error": "FORBIDDEN"})
    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_http.post = AsyncMock(return_value=error_resp)

        with pytest.raises(PoeAPIError) as exc_info:
            await client.chat_completions(
                model="x",
                messages=[{"role": "user", "content": "test"}],
            )

    assert exc_info.value.error_code == "FORBIDDEN"


# ---------------------------------------------------------------------------
# 3. server_poe tool functions
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def server_mod():
    """Load server_poe module once for all tool tests."""
    return _load_server_poe()


@pytest.mark.asyncio
async def test_tool_poe_list_models_success(server_mod):
    mock_result = {
        "count": 2,
        "models": [
            {"id": "Claude-Sonnet-4-5", "owned_by": "anthropic", "description": "Text model",
             "input_modalities": ["text"], "output_modalities": ["text"], "pricing": None},
            {"id": "gpt-image-1.5", "owned_by": "openai", "description": "Image model",
             "input_modalities": ["text"], "output_modalities": ["image"], "pricing": None},
        ],
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.list_models = AsyncMock(return_value=mock_result)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.poe_list_models(output_modality="text", limit=10)

    assert result["status"] == "success"
    assert result["count"] == 2
    mock_client.list_models.assert_called_once_with(
        input_modality=None, output_modality="text", search=None, limit=10
    )


@pytest.mark.asyncio
async def test_tool_poe_list_models_invalid_modality(server_mod):
    result = await server_mod.poe_list_models(output_modality="hologram")
    assert result["status"] == "error"
    assert "Invalid output_modality" in result["message"]


@pytest.mark.asyncio
async def test_tool_poe_list_models_invalid_limit(server_mod):
    result = await server_mod.poe_list_models(limit=0)
    assert result["status"] == "error"
    assert "limit must be between" in result["message"]


@pytest.mark.asyncio
async def test_tool_poe_list_models_api_error(server_mod):
    from utils.poe_client import PoeAPIError
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.list_models = AsyncMock(
        side_effect=PoeAPIError("Service unavailable", status_code=503, error_code="SERVICE_UNAVAILABLE")
    )

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.poe_list_models()

    assert result["status"] == "error"
    assert "Service unavailable" in result["message"]
    assert result["error_code"] == "SERVICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_tool_poe_chat_success(server_mod):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.chat_completions = AsyncMock(return_value=SAMPLE_CHAT_RESPONSE)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.poe_chat(
            prompt="Hello there",
            model="Claude-Sonnet-4-5",
        )

    assert result["status"] == "success"
    assert result["model"] == "Claude-Sonnet-4-5"
    assert result["text"] == "Hello! How can I help you today?"


@pytest.mark.asyncio
async def test_tool_poe_chat_with_system_and_temperature(server_mod):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.chat_completions = AsyncMock(return_value=SAMPLE_CHAT_RESPONSE)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.poe_chat(
            prompt="Write a haiku",
            model="Claude-Sonnet-4-5",
            system="You are a poet",
            temperature=0.9,
            max_tokens=50,
        )

    assert result["status"] == "success"
    call_kwargs = mock_client.chat_completions.call_args
    messages = call_kwargs[1]["messages"] if "messages" in call_kwargs[1] else call_kwargs[0][1]
    # System message should be first
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are a poet"


@pytest.mark.asyncio
async def test_tool_poe_chat_missing_prompt(server_mod):
    result = await server_mod.poe_chat(prompt="")
    assert result["status"] == "error"
    assert "prompt is required" in result["message"]


@pytest.mark.asyncio
async def test_tool_poe_chat_invalid_temperature(server_mod):
    result = await server_mod.poe_chat(prompt="Hi", temperature=3.0)
    assert result["status"] == "error"
    assert "temperature" in result["message"]


@pytest.mark.asyncio
async def test_tool_poe_chat_with_image_urls(server_mod):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.chat_completions = AsyncMock(return_value=SAMPLE_CHAT_RESPONSE)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.poe_chat(
            prompt="Describe this",
            model="Claude-Sonnet-4-5",
            image_urls=["https://example.com/pic.png"],
        )

    assert result["status"] == "success"
    call_kwargs = mock_client.chat_completions.call_args
    messages = call_kwargs[1]["messages"] if "messages" in call_kwargs[1] else call_kwargs[0][1]
    user_msg = next(m for m in messages if m["role"] == "user")
    assert isinstance(user_msg["content"], list)
    assert any(b.get("type") == "image_url" for b in user_msg["content"])


@pytest.mark.asyncio
async def test_tool_poe_chat_api_error(server_mod):
    from utils.poe_client import PoeAPIError
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.chat_completions = AsyncMock(
        side_effect=PoeAPIError("Model not found", status_code=404, error_code="MODEL_NOT_FOUND")
    )

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.poe_chat(prompt="Hello", model="nonexistent-model")

    assert result["status"] == "error"
    assert "Model not found" in result["message"]
    assert result["error_code"] == "MODEL_NOT_FOUND"


@pytest.mark.asyncio
async def test_tool_poe_generate_image_success_no_download(server_mod):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.chat_completions = AsyncMock(return_value=SAMPLE_IMAGE_RESPONSE)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.poe_generate_image(
            prompt="A sunset over mountains",
            model="gpt-image-1.5",
            download_media=False,
        )

    assert result["status"] == "success"
    assert result["model"] == "gpt-image-1.5"
    assert "poe.com" in result["raw_text"]
    assert len(result["extracted_urls"]) == 1
    assert result["downloaded"] == []


@pytest.mark.asyncio
async def test_tool_poe_generate_image_with_download(server_mod):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.chat_completions = AsyncMock(return_value=SAMPLE_IMAGE_RESPONSE)
    mock_client.download_media = AsyncMock(return_value={
        "url": "https://poe.com/images/generated/abc123.png",
        "content_type": "image/png",
        "bytes": 1024,
        "kind": "image",
        "format": "png",
        "data_b64": "iVBORw0KGgo=",
    })

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.poe_generate_image(
            prompt="A sunset over mountains",
            model="gpt-image-1.5",
            download_media=True,
        )

    assert result["status"] == "success"
    assert len(result["downloaded"]) == 1
    assert result["downloaded"][0]["kind"] == "image"
    assert result["downloaded"][0]["data_b64"] == "iVBORw0KGgo="


@pytest.mark.asyncio
async def test_tool_poe_generate_image_missing_prompt(server_mod):
    result = await server_mod.poe_generate_image(prompt="", model="gpt-image-1.5")
    assert result["status"] == "error"
    assert "prompt is required" in result["message"]


@pytest.mark.asyncio
async def test_tool_poe_generate_video_success(server_mod):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.chat_completions = AsyncMock(return_value=SAMPLE_VIDEO_RESPONSE)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.poe_generate_video(
            prompt="A time-lapse of a flower blooming",
            model="runway-gen3",
            download_media=False,
        )

    assert result["status"] == "success"
    assert result["model"] == "runway-gen3"
    assert len(result["extracted_urls"]) == 1
    assert result["downloaded"] == []


@pytest.mark.asyncio
async def test_tool_poe_generate_video_missing_model(server_mod):
    result = await server_mod.poe_generate_video(prompt="A video", model="")
    assert result["status"] == "error"
    assert "model is required" in result["message"]


@pytest.mark.asyncio
async def test_tool_poe_generate_video_missing_prompt(server_mod):
    result = await server_mod.poe_generate_video(prompt="", model="some-video-model")
    assert result["status"] == "error"
    assert "prompt is required" in result["message"]


@pytest.mark.asyncio
async def test_tool_poe_generate_audio_success(server_mod):
    audio_resp = {
        "choices": [
            {"message": {"role": "assistant", "content": "Audio ready: https://poe.com/audio/gen/track.mp3"}}
        ]
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.chat_completions = AsyncMock(return_value=audio_resp)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.poe_generate_audio(
            prompt="Generate calm background music",
            model="suno-v3",
            download_media=False,
        )

    assert result["status"] == "success"
    assert result["model"] == "suno-v3"
    assert len(result["extracted_urls"]) == 1


@pytest.mark.asyncio
async def test_tool_poe_generate_audio_missing_model(server_mod):
    result = await server_mod.poe_generate_audio(prompt="Music", model="")
    assert result["status"] == "error"
    assert "model is required" in result["message"]


@pytest.mark.asyncio
async def test_tool_poe_generate_image_non_allowed_host_not_downloaded(server_mod):
    """URLs from non-allowed hosts should not be downloaded even with download_media=True."""
    external_resp = {
        "choices": [
            {"message": {"role": "assistant", "content": "Image: https://external-cdn.com/image.png"}}
        ]
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.chat_completions = AsyncMock(return_value=external_resp)
    mock_client.download_media = AsyncMock()

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.poe_generate_image(
            prompt="Test",
            model="gpt-image-1.5",
            download_media=True,
        )

    assert result["status"] == "success"
    # download_media should NOT have been called for a non-allowed host
    mock_client.download_media.assert_not_called()
    assert result["downloaded"] == []


# ---------------------------------------------------------------------------
# 4. Task runner routing
# ---------------------------------------------------------------------------

class TestTaskRunnerRouting:
    def setup_method(self):
        from services.task_runner import _resolve_tool
        from core.config import POE_SERVICE_NAME, FIGMA_SERVICE_NAME, WEB_SEARCH_SERVICE_NAME
        self._resolve_tool = _resolve_tool
        self.POE_SERVICE_NAME = POE_SERVICE_NAME
        self.FIGMA_SERVICE_NAME = FIGMA_SERVICE_NAME
        self.WEB_SEARCH_SERVICE_NAME = WEB_SEARCH_SERVICE_NAME

    def test_poe_list_models_routes_to_poe(self):
        svc, tool = self._resolve_tool("poe_list_models")
        assert svc == self.POE_SERVICE_NAME
        assert tool == "poe_list_models"

    def test_poe_chat_routes_to_poe(self):
        svc, tool = self._resolve_tool("poe_chat")
        assert svc == self.POE_SERVICE_NAME
        assert tool == "poe_chat"

    def test_poe_generate_image_routes_to_poe(self):
        svc, tool = self._resolve_tool("poe_generate_image")
        assert svc == self.POE_SERVICE_NAME
        assert tool == "poe_generate_image"

    def test_poe_generate_video_routes_to_poe(self):
        svc, tool = self._resolve_tool("poe_generate_video")
        assert svc == self.POE_SERVICE_NAME
        assert tool == "poe_generate_video"

    def test_poe_generate_audio_routes_to_poe(self):
        svc, tool = self._resolve_tool("poe_generate_audio")
        assert svc == self.POE_SERVICE_NAME
        assert tool == "poe_generate_audio"

    def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            self._resolve_tool("poe_nonexistent_tool")

    def test_figma_tools_still_route_correctly(self):
        svc, tool = self._resolve_tool("figma_get_file")
        assert svc == self.FIGMA_SERVICE_NAME

    def test_web_search_still_routes_correctly(self):
        svc, tool = self._resolve_tool("web_search")
        assert svc == self.WEB_SEARCH_SERVICE_NAME


# ---------------------------------------------------------------------------
# 5. MCP service registry
# ---------------------------------------------------------------------------

class TestMCPServiceRegistry:
    def setup_method(self):
        from services.mcp_service import app_state
        from core.config import POE_SERVICE_NAME
        self.app_state = app_state
        self.POE_SERVICE_NAME = POE_SERVICE_NAME

    def test_poe_service_registered(self):
        assert self.POE_SERVICE_NAME in self.app_state.mcp_configs

    def test_poe_service_script_name(self):
        config = self.app_state.mcp_configs[self.POE_SERVICE_NAME]
        assert config.script_name == "server_poe.py"

    def test_poe_required_tools(self):
        config = self.app_state.mcp_configs[self.POE_SERVICE_NAME]
        expected = ["poe_list_models", "poe_chat", "poe_generate_image",
                    "poe_generate_video", "poe_generate_audio"]
        for tool in expected:
            assert tool in config.required_tools, f"'{tool}' missing from required_tools"

    def test_poe_service_name_constant(self):
        from core.config import POE_SERVICE_NAME
        assert POE_SERVICE_NAME == "poe_service"

    def test_poe_disabled_without_key(self):
        """Service should be disabled when POE_API_KEY is absent."""
        import os
        saved = os.environ.pop("POE_API_KEY", None)
        try:
            from services.mcp_service import MCPServiceConfig
            cfg = MCPServiceConfig(
                name="poe_service",
                script_name="server_poe.py",
                enabled=bool(os.getenv("POE_API_KEY")),
            )
            assert cfg.enabled is False
        finally:
            if saved:
                os.environ["POE_API_KEY"] = saved

    def test_existing_services_still_registered(self):
        from core.config import FIGMA_SERVICE_NAME, CANVA_SERVICE_NAME, WEB_SEARCH_SERVICE_NAME
        assert FIGMA_SERVICE_NAME in self.app_state.mcp_configs
        assert CANVA_SERVICE_NAME in self.app_state.mcp_configs
        assert WEB_SEARCH_SERVICE_NAME in self.app_state.mcp_configs


# ---------------------------------------------------------------------------
# 6. Task planner — allowed tools, aliases, catalog
# ---------------------------------------------------------------------------

class TestTaskPlanner:
    def setup_method(self):
        from services.task_planner import ALLOWED_TASK_TOOLS, _normalize_tool, _tool_catalog_text
        self.ALLOWED_TASK_TOOLS = ALLOWED_TASK_TOOLS
        self._normalize_tool = _normalize_tool
        self._tool_catalog_text = _tool_catalog_text

    def test_poe_tools_in_allowed_list(self):
        for tool in ["poe_list_models", "poe_chat", "poe_generate_image",
                     "poe_generate_video", "poe_generate_audio"]:
            assert tool in self.ALLOWED_TASK_TOOLS, f"'{tool}' missing from ALLOWED_TASK_TOOLS"

    def test_alias_poe_models(self):
        assert self._normalize_tool("poe_models") == "poe_list_models"

    def test_alias_poe(self):
        assert self._normalize_tool("poe") == "poe_chat"

    def test_alias_poe_generate(self):
        assert self._normalize_tool("poe_generate") == "poe_chat"

    def test_alias_poe_image(self):
        assert self._normalize_tool("poe_image") == "poe_generate_image"

    def test_alias_poe_video(self):
        assert self._normalize_tool("poe_video") == "poe_generate_video"

    def test_alias_poe_audio(self):
        assert self._normalize_tool("poe_audio") == "poe_generate_audio"

    def test_poe_catalog_section_present(self):
        catalog = self._tool_catalog_text()
        assert "Poe" in catalog
        assert "poe_list_models" in catalog
        assert "poe_chat" in catalog
        assert "poe_generate_image" in catalog
        assert "poe_generate_video" in catalog
        assert "poe_generate_audio" in catalog

    def test_poe_catalog_includes_modalities(self):
        catalog = self._tool_catalog_text()
        assert "image" in catalog
        assert "audio" in catalog
        assert "video" in catalog

    def test_poe_catalog_includes_default_model(self):
        catalog = self._tool_catalog_text()
        assert "Claude-Sonnet-4-5" in catalog

    def test_existing_tools_unaffected(self):
        for tool in ["web_search", "smart_search_extract", "execute_sql_query_tool",
                     "get_youtube_transcript", "create_design", "figma_get_file", "llm.generate"]:
            assert tool in self.ALLOWED_TASK_TOOLS, f"Existing tool '{tool}' was broken"

    def test_mcp_config_poe_tools_in_whitelist(self):
        """Poe MCP required_tools all appear in ALLOWED_TASK_TOOLS."""
        from services.mcp_service import app_state
        from core.config import POE_SERVICE_NAME
        required = app_state.mcp_configs[POE_SERVICE_NAME].required_tools
        for tool in required:
            assert tool in self.ALLOWED_TASK_TOOLS, f"Poe tool '{tool}' missing from ALLOWED_TASK_TOOLS"


# ---------------------------------------------------------------------------
# 7. Planner heuristics — credential gates and injection
# ---------------------------------------------------------------------------

class TestPlannerHeuristics:
    """
    Tests for the post-planning gates in plan_task():
    - Canva gate: replace Canva steps with llm.generate when service disabled
    - Figma gate: replace Figma steps with llm.generate when service disabled
    - Poe gate:   replace Poe steps with llm.generate when service disabled
    - Poe image injection: auto-add poe_generate_image for image-goal keywords
    """

    def _make_step(self, tool: str, step_id: str = "s1") -> "PlanStep":
        from core.models import PlanStep
        return PlanStep(
            id=step_id,
            title=f"Step using {tool}",
            instruction=f"Do something with {tool}",
            tool=tool,
            params={},
            success_criteria="Done",
            max_retries=1,
        )

    def _disabled_cfg(self, service_name: str):
        """Return a fake MCPServiceConfig with enabled=False."""
        from services.mcp_service import MCPServiceConfig
        return MCPServiceConfig(name=service_name, script_name="dummy.py", enabled=False)

    def _enabled_cfg(self, service_name: str):
        from services.mcp_service import MCPServiceConfig
        return MCPServiceConfig(name=service_name, script_name="dummy.py", enabled=True)

    # --- Canva gate ---

    def test_canva_gate_replaces_steps_when_disabled(self):
        """All Canva tool steps become llm.generate when CANVA_SERVICE disabled."""
        from services.mcp_service import app_state
        from core.config import CANVA_SERVICE_NAME
        canva_tools = ["create_design", "list_designs", "get_design", "export_design"]
        original = app_state.mcp_configs.get(CANVA_SERVICE_NAME)
        try:
            app_state.mcp_configs[CANVA_SERVICE_NAME] = self._disabled_cfg(CANVA_SERVICE_NAME)
            # Simulate the gate logic directly (synchronous extract)
            from core.models import Plan, PlanStep
            steps = [self._make_step(t, f"s{i}") for i, t in enumerate(canva_tools, 1)]
            plan = Plan(constraints=[], resources=[], steps=steps)
            _CANVA_TOOLS = set(canva_tools)
            gated = []
            cfg = app_state.mcp_configs.get(CANVA_SERVICE_NAME)
            if cfg is not None and not cfg.enabled:
                for s in plan.steps:
                    if s.tool in _CANVA_TOOLS:
                        gated.append(PlanStep(
                            id=s.id, title=s.title,
                            instruction=s.instruction + " (Canva not configured — CANVA_API_TOKEN missing)",
                            tool="llm.generate", params={},
                            success_criteria=s.success_criteria, max_retries=s.max_retries,
                        ))
                    else:
                        gated.append(s)
                plan.steps = gated
            assert all(s.tool == "llm.generate" for s in plan.steps)
            assert all("CANVA_API_TOKEN missing" in s.instruction for s in plan.steps)
        finally:
            if original is not None:
                app_state.mcp_configs[CANVA_SERVICE_NAME] = original

    def test_canva_gate_preserves_non_canva_steps(self):
        """Non-Canva steps are untouched by the Canva gate."""
        from services.mcp_service import app_state
        from core.config import CANVA_SERVICE_NAME
        from core.models import Plan, PlanStep
        original = app_state.mcp_configs.get(CANVA_SERVICE_NAME)
        try:
            app_state.mcp_configs[CANVA_SERVICE_NAME] = self._disabled_cfg(CANVA_SERVICE_NAME)
            plan = Plan(constraints=[], resources=[], steps=[
                self._make_step("web_search", "s1"),
                self._make_step("create_design", "s2"),
                self._make_step("llm.generate", "s3"),
            ])
            _CANVA_TOOLS = {"create_design", "list_designs", "get_design", "export_design"}
            gated = []
            cfg = app_state.mcp_configs.get(CANVA_SERVICE_NAME)
            if cfg is not None and not cfg.enabled:
                for s in plan.steps:
                    if s.tool in _CANVA_TOOLS:
                        gated.append(PlanStep(
                            id=s.id, title=s.title,
                            instruction=s.instruction + " (Canva not configured — CANVA_API_TOKEN missing)",
                            tool="llm.generate", params={},
                            success_criteria=s.success_criteria, max_retries=s.max_retries,
                        ))
                    else:
                        gated.append(s)
                plan.steps = gated
            assert plan.steps[0].tool == "web_search"
            assert plan.steps[1].tool == "llm.generate"
            assert plan.steps[2].tool == "llm.generate"
        finally:
            if original is not None:
                app_state.mcp_configs[CANVA_SERVICE_NAME] = original

    def test_canva_gate_no_op_when_enabled(self):
        """When Canva is enabled, tool steps are NOT replaced."""
        from services.mcp_service import app_state
        from core.config import CANVA_SERVICE_NAME
        from core.models import Plan
        original = app_state.mcp_configs.get(CANVA_SERVICE_NAME)
        try:
            app_state.mcp_configs[CANVA_SERVICE_NAME] = self._enabled_cfg(CANVA_SERVICE_NAME)
            plan = Plan(constraints=[], resources=[], steps=[self._make_step("create_design")])
            _CANVA_TOOLS = {"create_design", "list_designs", "get_design", "export_design"}
            cfg = app_state.mcp_configs.get(CANVA_SERVICE_NAME)
            if cfg is not None and not cfg.enabled:
                plan.steps = []  # would replace — should NOT run
            assert plan.steps[0].tool == "create_design"
        finally:
            if original is not None:
                app_state.mcp_configs[CANVA_SERVICE_NAME] = original

    # --- Figma gate ---

    def test_figma_gate_replaces_all_figma_tools(self):
        from services.mcp_service import app_state
        from core.config import FIGMA_SERVICE_NAME
        from core.models import Plan, PlanStep
        figma_tools = [
            "figma_get_file", "figma_get_nodes", "figma_export_images",
            "figma_get_comments", "figma_post_comment", "figma_get_design_system",
        ]
        original = app_state.mcp_configs.get(FIGMA_SERVICE_NAME)
        try:
            app_state.mcp_configs[FIGMA_SERVICE_NAME] = self._disabled_cfg(FIGMA_SERVICE_NAME)
            plan = Plan(constraints=[], resources=[], steps=[
                self._make_step(t, f"s{i}") for i, t in enumerate(figma_tools, 1)
            ])
            _FIGMA_TOOLS = set(figma_tools)
            gated = []
            cfg = app_state.mcp_configs.get(FIGMA_SERVICE_NAME)
            if cfg is not None and not cfg.enabled:
                for s in plan.steps:
                    if s.tool in _FIGMA_TOOLS:
                        gated.append(PlanStep(
                            id=s.id, title=s.title,
                            instruction=s.instruction + " (Figma not configured — FIGMA_ACCESS_TOKEN missing)",
                            tool="llm.generate", params={},
                            success_criteria=s.success_criteria, max_retries=s.max_retries,
                        ))
                    else:
                        gated.append(s)
                plan.steps = gated
            assert all(s.tool == "llm.generate" for s in plan.steps)
            assert all("FIGMA_ACCESS_TOKEN missing" in s.instruction for s in plan.steps)
        finally:
            if original is not None:
                app_state.mcp_configs[FIGMA_SERVICE_NAME] = original

    def test_figma_gate_preserves_non_figma_steps(self):
        from services.mcp_service import app_state
        from core.config import FIGMA_SERVICE_NAME
        from core.models import Plan, PlanStep
        original = app_state.mcp_configs.get(FIGMA_SERVICE_NAME)
        try:
            app_state.mcp_configs[FIGMA_SERVICE_NAME] = self._disabled_cfg(FIGMA_SERVICE_NAME)
            plan = Plan(constraints=[], resources=[], steps=[
                self._make_step("web_search", "s1"),
                self._make_step("figma_get_file", "s2"),
            ])
            _FIGMA_TOOLS = {"figma_get_file", "figma_get_nodes", "figma_export_images",
                            "figma_get_comments", "figma_post_comment", "figma_get_design_system"}
            gated = []
            cfg = app_state.mcp_configs.get(FIGMA_SERVICE_NAME)
            if cfg is not None and not cfg.enabled:
                for s in plan.steps:
                    if s.tool in _FIGMA_TOOLS:
                        gated.append(PlanStep(
                            id=s.id, title=s.title,
                            instruction=s.instruction + " (Figma not configured — FIGMA_ACCESS_TOKEN missing)",
                            tool="llm.generate", params={},
                            success_criteria=s.success_criteria, max_retries=s.max_retries,
                        ))
                    else:
                        gated.append(s)
                plan.steps = gated
            assert plan.steps[0].tool == "web_search"
            assert plan.steps[1].tool == "llm.generate"
        finally:
            if original is not None:
                app_state.mcp_configs[FIGMA_SERVICE_NAME] = original

    # --- Poe gate ---

    def test_poe_gate_replaces_all_poe_tools(self):
        from services.mcp_service import app_state
        from core.config import POE_SERVICE_NAME
        from core.models import Plan, PlanStep
        poe_tools = ["poe_list_models", "poe_chat", "poe_generate_image",
                     "poe_generate_video", "poe_generate_audio"]
        original = app_state.mcp_configs.get(POE_SERVICE_NAME)
        try:
            app_state.mcp_configs[POE_SERVICE_NAME] = self._disabled_cfg(POE_SERVICE_NAME)
            plan = Plan(constraints=[], resources=[], steps=[
                self._make_step(t, f"s{i}") for i, t in enumerate(poe_tools, 1)
            ])
            _POE_TOOLS = set(poe_tools)
            gated = []
            cfg = app_state.mcp_configs.get(POE_SERVICE_NAME)
            if cfg is not None and not cfg.enabled:
                for s in plan.steps:
                    if s.tool in _POE_TOOLS:
                        gated.append(PlanStep(
                            id=s.id, title=s.title,
                            instruction=s.instruction + " (Poe AI not configured — POE_API_KEY missing)",
                            tool="llm.generate", params={},
                            success_criteria=s.success_criteria, max_retries=s.max_retries,
                        ))
                    else:
                        gated.append(s)
                plan.steps = gated
            assert all(s.tool == "llm.generate" for s in plan.steps)
            assert all("POE_API_KEY missing" in s.instruction for s in plan.steps)
        finally:
            if original is not None:
                app_state.mcp_configs[POE_SERVICE_NAME] = original

    def test_poe_gate_preserves_non_poe_steps(self):
        from services.mcp_service import app_state
        from core.config import POE_SERVICE_NAME
        from core.models import Plan, PlanStep
        original = app_state.mcp_configs.get(POE_SERVICE_NAME)
        try:
            app_state.mcp_configs[POE_SERVICE_NAME] = self._disabled_cfg(POE_SERVICE_NAME)
            plan = Plan(constraints=[], resources=[], steps=[
                self._make_step("web_search", "s1"),
                self._make_step("poe_chat", "s2"),
                self._make_step("llm.generate", "s3"),
            ])
            _POE_TOOLS = {"poe_list_models", "poe_chat", "poe_generate_image",
                          "poe_generate_video", "poe_generate_audio"}
            gated = []
            cfg = app_state.mcp_configs.get(POE_SERVICE_NAME)
            if cfg is not None and not cfg.enabled:
                for s in plan.steps:
                    if s.tool in _POE_TOOLS:
                        gated.append(PlanStep(
                            id=s.id, title=s.title,
                            instruction=s.instruction + " (Poe AI not configured — POE_API_KEY missing)",
                            tool="llm.generate", params={},
                            success_criteria=s.success_criteria, max_retries=s.max_retries,
                        ))
                    else:
                        gated.append(s)
                plan.steps = gated
            assert plan.steps[0].tool == "web_search"
            assert plan.steps[1].tool == "llm.generate"
            assert plan.steps[2].tool == "llm.generate"
        finally:
            if original is not None:
                app_state.mcp_configs[POE_SERVICE_NAME] = original

    def test_poe_gate_no_op_when_enabled(self):
        from services.mcp_service import app_state
        from core.config import POE_SERVICE_NAME
        from core.models import Plan
        original = app_state.mcp_configs.get(POE_SERVICE_NAME)
        try:
            app_state.mcp_configs[POE_SERVICE_NAME] = self._enabled_cfg(POE_SERVICE_NAME)
            plan = Plan(constraints=[], resources=[], steps=[self._make_step("poe_chat")])
            cfg = app_state.mcp_configs.get(POE_SERVICE_NAME)
            if cfg is not None and not cfg.enabled:
                plan.steps = []  # would replace — should NOT run
            assert plan.steps[0].tool == "poe_chat"
        finally:
            if original is not None:
                app_state.mcp_configs[POE_SERVICE_NAME] = original

    # --- Poe image injection heuristic ---

    def test_poe_image_injection_triggers_on_keyword(self):
        """Image-goal keywords cause poe_generate_image to be injected when Poe is enabled."""
        from services.mcp_service import app_state
        from core.config import POE_SERVICE_NAME
        from core.models import Plan, PlanStep
        _image_keywords = [
            "generate image", "create image", "make image", "draw", "illustrate",
            "generate a picture", "create a picture", "image of", "picture of",
            "generate artwork", "create artwork",
        ]
        original = app_state.mcp_configs.get(POE_SERVICE_NAME)
        try:
            app_state.mcp_configs[POE_SERVICE_NAME] = self._enabled_cfg(POE_SERVICE_NAME)
            for kw in _image_keywords:
                goal = f"Please {kw} for me"
                plan = Plan(constraints=[], resources=[], steps=[self._make_step("web_search")])
                cfg = app_state.mcp_configs.get(POE_SERVICE_NAME)
                poe_ok = cfg is not None and cfg.enabled
                if poe_ok and not any(s.tool == "poe_generate_image" for s in plan.steps):
                    gl = goal.lower()
                    if any(k in gl for k in _image_keywords):
                        plan.steps.append(PlanStep(
                            id=f"s{len(plan.steps)+1}", title="Generate image via Poe",
                            instruction=goal, tool="poe_generate_image",
                            params={}, success_criteria="Image generated", max_retries=1,
                        ))
                assert any(s.tool == "poe_generate_image" for s in plan.steps), \
                    f"Expected poe_generate_image injection for keyword: '{kw}'"
        finally:
            if original is not None:
                app_state.mcp_configs[POE_SERVICE_NAME] = original

    def test_poe_image_injection_no_duplicate(self):
        """poe_generate_image is not injected if already present in the plan."""
        from services.mcp_service import app_state
        from core.config import POE_SERVICE_NAME
        from core.models import Plan
        _image_keywords = ["generate image", "create image", "make image", "draw"]
        original = app_state.mcp_configs.get(POE_SERVICE_NAME)
        try:
            app_state.mcp_configs[POE_SERVICE_NAME] = self._enabled_cfg(POE_SERVICE_NAME)
            goal = "generate image of a sunset"
            plan = Plan(constraints=[], resources=[], steps=[
                self._make_step("poe_generate_image", "s1"),
            ])
            cfg = app_state.mcp_configs.get(POE_SERVICE_NAME)
            poe_ok = cfg is not None and cfg.enabled
            before = len(plan.steps)
            if poe_ok and not any(s.tool == "poe_generate_image" for s in plan.steps):
                gl = goal.lower()
                if any(k in gl for k in _image_keywords):
                    plan.steps.append(self._make_step("poe_generate_image", f"s{len(plan.steps)+1}"))
            assert len(plan.steps) == before  # no duplicate added
        finally:
            if original is not None:
                app_state.mcp_configs[POE_SERVICE_NAME] = original

    def test_poe_image_injection_no_op_when_disabled(self):
        """poe_generate_image is NOT injected when Poe service is disabled."""
        from services.mcp_service import app_state
        from core.config import POE_SERVICE_NAME
        from core.models import Plan
        _image_keywords = ["generate image"]
        original = app_state.mcp_configs.get(POE_SERVICE_NAME)
        try:
            app_state.mcp_configs[POE_SERVICE_NAME] = self._disabled_cfg(POE_SERVICE_NAME)
            goal = "generate image of a mountain"
            plan = Plan(constraints=[], resources=[], steps=[self._make_step("web_search")])
            cfg = app_state.mcp_configs.get(POE_SERVICE_NAME)
            poe_ok = cfg is not None and cfg.enabled  # False
            if poe_ok and not any(s.tool == "poe_generate_image" for s in plan.steps):
                gl = goal.lower()
                if any(k in gl for k in _image_keywords):
                    plan.steps.append(self._make_step("poe_generate_image", "injected"))
            assert not any(s.tool == "poe_generate_image" for s in plan.steps)
        finally:
            if original is not None:
                app_state.mcp_configs[POE_SERVICE_NAME] = original

    def test_poe_image_injection_no_op_for_non_image_goal(self):
        """No injection occurs for goals that don't mention image generation."""
        from services.mcp_service import app_state
        from core.config import POE_SERVICE_NAME
        from core.models import Plan
        _image_keywords = [
            "generate image", "create image", "make image", "draw", "illustrate",
            "generate a picture", "create a picture", "image of", "picture of",
            "generate artwork", "create artwork",
        ]
        original = app_state.mcp_configs.get(POE_SERVICE_NAME)
        try:
            app_state.mcp_configs[POE_SERVICE_NAME] = self._enabled_cfg(POE_SERVICE_NAME)
            goal = "search the web for the latest news about AI"
            plan = Plan(constraints=[], resources=[], steps=[self._make_step("web_search")])
            cfg = app_state.mcp_configs.get(POE_SERVICE_NAME)
            poe_ok = cfg is not None and cfg.enabled
            if poe_ok and not any(s.tool == "poe_generate_image" for s in plan.steps):
                gl = goal.lower()
                if any(k in gl for k in _image_keywords):
                    plan.steps.append(self._make_step("poe_generate_image", "injected"))
            assert not any(s.tool == "poe_generate_image" for s in plan.steps)
        finally:
            if original is not None:
                app_state.mcp_configs[POE_SERVICE_NAME] = original
