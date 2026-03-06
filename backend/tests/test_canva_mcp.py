"""
Tests for the Canva MCP server integration.

Covers:
- Pydantic model validation (no API calls)
- CanvaClient methods with mocked httpx responses
- server_canva tool functions with mocked CanvaClient
- Task runner routing and planner registration
"""
import importlib.util
import json
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

def _load_server_canva():
    """Load server_canva.py with a fake token so the import doesn't raise."""
    os.environ.setdefault("CANVA_API_TOKEN", "test_fake_token_for_testing")
    spec = importlib.util.spec_from_file_location(
        "server_canva_test",
        str(BACKEND_DIR / "server_canva.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# 1. Pydantic model validation
# ---------------------------------------------------------------------------

class TestModels:
    """Pydantic model validation — no network calls."""

    def setup_method(self):
        from utils.canva_client import (
            CanvaAPIError,
            CreateDesignRequest,
            DesignPreset,
            DesignSize,
            DesignUnit,
            ExportDesignRequest,
            ExportFormat,
        )
        self.CreateDesignRequest = CreateDesignRequest
        self.DesignPreset = DesignPreset
        self.DesignSize = DesignSize
        self.DesignUnit = DesignUnit
        self.ExportDesignRequest = ExportDesignRequest
        self.ExportFormat = ExportFormat
        self.CanvaAPIError = CanvaAPIError

    def test_create_design_with_preset(self):
        req = self.CreateDesignRequest(title="My Design", preset=self.DesignPreset.PRESENTATION)
        assert req.title == "My Design"
        assert req.preset == self.DesignPreset.PRESENTATION
        assert req.size is None

    def test_create_design_with_custom_size(self):
        size = self.DesignSize(width=800, height=600, unit=self.DesignUnit.PIXELS)
        req = self.CreateDesignRequest(title="Custom", preset=self.DesignPreset.CUSTOM, size=size)
        assert req.size.width == 800
        assert req.size.height == 600

    def test_create_design_requires_preset_or_size(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="Either preset or size must be provided"):
            self.CreateDesignRequest(title="Bad")

    def test_create_design_custom_without_size_fails(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="size must be provided"):
            self.CreateDesignRequest(title="Bad", preset=self.DesignPreset.CUSTOM)

    def test_export_request_valid(self):
        req = self.ExportDesignRequest(design_id="abc123", format=self.ExportFormat.PNG)
        assert req.design_id == "abc123"
        assert req.format == self.ExportFormat.PNG

    def test_export_quality_only_for_jpg(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="quality is only valid for JPG"):
            self.ExportDesignRequest(design_id="abc", format=self.ExportFormat.PNG, quality=80)

    def test_export_quality_valid_for_jpg(self):
        req = self.ExportDesignRequest(
            design_id="abc", format=self.ExportFormat.JPG, quality=85
        )
        assert req.quality == 85

    def test_canva_api_error_attributes(self):
        err = self.CanvaAPIError(
            message="Not found",
            status_code=404,
            error_code="NOT_FOUND",
        )
        assert err.message == "Not found"
        assert err.status_code == 404
        assert err.error_code == "NOT_FOUND"
        assert str(err) == "Not found"


# ---------------------------------------------------------------------------
# 2. CanvaClient with mocked httpx
# ---------------------------------------------------------------------------

def _make_mock_response(json_data: dict, status_code: int = 200):
    """Build a mock httpx.Response that returns json_data."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


def _make_error_response(status_code: int, error_body: dict):
    import httpx
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = error_body
    http_err = httpx.HTTPStatusError(
        message=f"HTTP {status_code}",
        request=MagicMock(),
        response=mock,
    )
    mock.raise_for_status.side_effect = http_err
    return mock


SAMPLE_DESIGN_RESPONSE = {
    "id": "design_001",
    "title": "Test Design",
    "width": 1920,
    "height": 1080,
    "urls": {"edit": "https://canva.com/edit/design_001"},
    "thumbnail": {"url": "https://canva.com/thumb/design_001.png"},
    "type": "presentation",
    "owner": {"id": "user_001"},
    "team": {"id": "team_001"},
}


@pytest.mark.asyncio
async def test_client_list_designs():
    from utils.canva_client import CanvaClient
    client = CanvaClient(api_token="fake_token")
    list_response = _make_mock_response({
        "items": [SAMPLE_DESIGN_RESPONSE],
        "continuation": "next_token_abc",
        "total_count": 1,
    })
    client.client.get = AsyncMock(return_value=list_response)

    result = await client.list_designs(limit=10)

    assert result["items"][0]["id"] == "design_001"
    assert result["next_page_token"] == "next_token_abc"
    assert result["total_count"] == 1
    await client.close()


@pytest.mark.asyncio
async def test_client_get_design():
    from utils.canva_client import CanvaClient
    client = CanvaClient(api_token="fake_token")
    client.client.get = AsyncMock(return_value=_make_mock_response(SAMPLE_DESIGN_RESPONSE))

    design = await client.get_design("design_001")

    assert design["id"] == "design_001"
    assert design["title"] == "Test Design"
    assert design["url"] == "https://canva.com/edit/design_001"
    assert design["thumbnail_url"] == "https://canva.com/thumb/design_001.png"
    await client.close()


@pytest.mark.asyncio
async def test_client_create_design_with_preset():
    from utils.canva_client import CanvaClient, CreateDesignRequest, DesignPreset
    client = CanvaClient(api_token="fake_token")
    client.client.post = AsyncMock(return_value=_make_mock_response(SAMPLE_DESIGN_RESPONSE))

    request = CreateDesignRequest(title="My Slides", preset=DesignPreset.PRESENTATION)
    design = await client.create_design(request)

    assert design["id"] == "design_001"
    call_kwargs = client.client.post.call_args
    payload = call_kwargs[1]["json"]
    assert payload["title"] == "My Slides"
    assert payload["preset"] == "presentation"
    await client.close()


@pytest.mark.asyncio
async def test_client_export_design_completes_immediately():
    from utils.canva_client import CanvaClient, ExportDesignRequest, ExportFormat
    client = CanvaClient(api_token="fake_token")
    export_response = {
        "id": "job_001",
        "status": "completed",
        "url": "https://cdn.canva.com/export/file.png",
        "file_size_bytes": 204800,
    }
    client.client.post = AsyncMock(return_value=_make_mock_response(export_response))

    request = ExportDesignRequest(design_id="design_001", format=ExportFormat.PNG)
    result = await client.export_design(request)

    assert result["status"] == "completed"
    assert result["download_url"] == "https://cdn.canva.com/export/file.png"
    assert result["job_id"] == "job_001"
    await client.close()


@pytest.mark.asyncio
async def test_client_export_design_polls_until_done():
    from utils.canva_client import CanvaClient, ExportDesignRequest, ExportFormat
    client = CanvaClient(api_token="fake_token")

    # POST starts the job (pending)
    post_response = _make_mock_response({"id": "job_002", "status": "pending"})
    # GET polls: first still in_progress, then completed
    poll_responses = [
        _make_mock_response({"id": "job_002", "status": "in_progress"}),
        _make_mock_response({
            "id": "job_002",
            "status": "completed",
            "url": "https://cdn.canva.com/export/file2.pdf",
            "file_size_bytes": 1024,
        }),
    ]
    client.client.post = AsyncMock(return_value=post_response)
    client.client.get = AsyncMock(side_effect=poll_responses)

    with patch("utils.canva_client.asyncio.sleep", new_callable=AsyncMock):
        request = ExportDesignRequest(design_id="design_001", format=ExportFormat.PDF)
        result = await client.export_design(request)

    assert result["status"] == "completed"
    assert result["download_url"] == "https://cdn.canva.com/export/file2.pdf"
    assert client.client.get.call_count == 2
    await client.close()


@pytest.mark.asyncio
async def test_client_api_error_propagates():
    from utils.canva_client import CanvaClient, CanvaAPIError
    client = CanvaClient(api_token="fake_token")
    error_response = _make_error_response(404, {"error": "DESIGN_NOT_FOUND", "message": "Design not found"})
    client.client.get = AsyncMock(return_value=error_response)

    with pytest.raises(CanvaAPIError) as exc_info:
        await client.get_design("nonexistent_id")

    assert exc_info.value.status_code == 404
    assert exc_info.value.error_code == "DESIGN_NOT_FOUND"
    await client.close()


# ---------------------------------------------------------------------------
# 3. server_canva tool functions
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def server_mod():
    """Load server_canva module once for all tool tests."""
    return _load_server_canva()


@pytest.mark.asyncio
async def test_tool_create_design_success(server_mod):
    mock_design = {
        "id": "design_001", "title": "My Slides",
        "url": "https://canva.com/edit/design_001",
        "thumbnail_url": None, "width": 1920, "height": 1080,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
        "type": "presentation", "owner_id": None, "team_id": None,
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.create_design = AsyncMock(return_value=mock_design)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.create_design(title="My Slides", preset="presentation")

    assert result["status"] == "success"
    assert result["id"] == "design_001"
    assert result["url"] == "https://canva.com/edit/design_001"


@pytest.mark.asyncio
async def test_tool_create_design_invalid_preset(server_mod):
    result = await server_mod.create_design(title="Test", preset="nonexistent_preset")
    assert result["status"] == "error"
    assert "Invalid preset" in result["message"]


@pytest.mark.asyncio
async def test_tool_create_design_custom_missing_dimensions(server_mod):
    result = await server_mod.create_design(title="Custom", preset="custom")
    assert result["status"] == "error"
    assert "width and height are required" in result["message"]


@pytest.mark.asyncio
async def test_tool_create_design_api_error(server_mod):
    from utils.canva_client import CanvaAPIError
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.create_design = AsyncMock(
        side_effect=CanvaAPIError("Unauthorized", status_code=401, error_code="UNAUTHORIZED")
    )

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.create_design(title="Test", preset="presentation")

    assert result["status"] == "error"
    assert "Unauthorized" in result["message"]
    assert result["error_code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_tool_list_designs_success(server_mod):
    mock_result = {
        "items": [{"id": "d1", "title": "Design 1"}],
        "next_page_token": None,
        "total_count": 1,
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.list_designs = AsyncMock(return_value=mock_result)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.list_designs(limit=10)

    assert result["status"] == "success"
    assert len(result["items"]) == 1
    assert result["items"][0]["id"] == "d1"


@pytest.mark.asyncio
async def test_tool_get_design_success(server_mod):
    mock_design = {"id": "design_001", "title": "My Design", "url": "https://canva.com/edit/design_001"}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_design = AsyncMock(return_value=mock_design)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.get_design("design_001")

    assert result["status"] == "success"
    assert result["id"] == "design_001"


@pytest.mark.asyncio
async def test_tool_get_design_missing_id(server_mod):
    result = await server_mod.get_design("")
    assert result["status"] == "error"
    assert "design_id is required" in result["message"]


@pytest.mark.asyncio
async def test_tool_export_design_success(server_mod):
    mock_result = {
        "job_id": "job_001", "status": "completed",
        "design_id": "design_001", "format": "png",
        "download_url": "https://cdn.canva.com/export/out.png",
        "file_size_bytes": 50000, "error_code": None, "error_message": None,
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.export_design = AsyncMock(return_value=mock_result)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.export_design("design_001", format="png")

    # Export tools return the job status ("completed"/"failed") as "status",
    # not the tool-call sentinel "success" used by create/list/get.
    assert result["status"] == "completed"
    assert result["download_url"] == "https://cdn.canva.com/export/out.png"
    assert result["job_id"] == "job_001"


@pytest.mark.asyncio
async def test_tool_export_design_invalid_format(server_mod):
    result = await server_mod.export_design("design_001", format="bmp")
    assert result["status"] == "error"
    assert "Invalid format" in result["message"]


@pytest.mark.asyncio
async def test_tool_export_design_pages_parsed(server_mod):
    mock_result = {
        "job_id": "job_002", "status": "completed",
        "design_id": "design_001", "format": "pdf",
        "download_url": "https://cdn.canva.com/export/out.pdf",
        "file_size_bytes": 10000, "error_code": None, "error_message": None,
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.export_design = AsyncMock(return_value=mock_result)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.export_design("design_001", format="pdf", pages="1,3")

    assert result["status"] == "completed"
    # Verify pages were parsed and passed to the client
    called_request = mock_client.export_design.call_args[0][0]
    assert called_request.pages == [1, 3]


@pytest.mark.asyncio
async def test_tool_export_design_invalid_pages(server_mod):
    result = await server_mod.export_design("design_001", pages="one,two")
    assert result["status"] == "error"
    assert "comma-separated integers" in result["message"]


# ---------------------------------------------------------------------------
# 4. Task runner routing
# ---------------------------------------------------------------------------

class TestTaskRunnerRouting:
    def setup_method(self):
        from services.task_runner import _resolve_tool
        from core.config import CANVA_SERVICE_NAME
        self._resolve_tool = _resolve_tool
        self.CANVA_SERVICE_NAME = CANVA_SERVICE_NAME

    def test_create_design_routes_to_canva(self):
        svc, tool = self._resolve_tool("create_design")
        assert svc == self.CANVA_SERVICE_NAME
        assert tool == "create_design"

    def test_list_designs_routes_to_canva(self):
        svc, tool = self._resolve_tool("list_designs")
        assert svc == self.CANVA_SERVICE_NAME
        assert tool == "list_designs"

    def test_get_design_routes_to_canva(self):
        svc, tool = self._resolve_tool("get_design")
        assert svc == self.CANVA_SERVICE_NAME
        assert tool == "get_design"

    def test_export_design_routes_to_canva(self):
        svc, tool = self._resolve_tool("export_design")
        assert svc == self.CANVA_SERVICE_NAME
        assert tool == "export_design"

    def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            self._resolve_tool("canva_magic_tool")

    def test_web_search_still_routes_correctly(self):
        from core.config import WEB_SEARCH_SERVICE_NAME
        svc, tool = self._resolve_tool("web_search")
        assert svc == WEB_SEARCH_SERVICE_NAME


# ---------------------------------------------------------------------------
# 5. MCP service registry
# ---------------------------------------------------------------------------

class TestMCPServiceRegistry:
    def setup_method(self):
        from services.mcp_service import app_state
        from core.config import CANVA_SERVICE_NAME
        self.app_state = app_state
        self.CANVA_SERVICE_NAME = CANVA_SERVICE_NAME

    def test_canva_service_registered(self):
        assert self.CANVA_SERVICE_NAME in self.app_state.mcp_configs

    def test_canva_service_script_name(self):
        config = self.app_state.mcp_configs[self.CANVA_SERVICE_NAME]
        assert config.script_name == "server_canva.py"

    def test_canva_required_tools(self):
        config = self.app_state.mcp_configs[self.CANVA_SERVICE_NAME]
        assert "create_design" in config.required_tools
        assert "list_designs" in config.required_tools
        assert "get_design" in config.required_tools
        assert "export_design" in config.required_tools

    def test_canva_service_name_constant(self):
        from core.config import CANVA_SERVICE_NAME
        assert CANVA_SERVICE_NAME == "canva_service"


# ---------------------------------------------------------------------------
# 6. Task planner — allowed tools, aliases, catalog
# ---------------------------------------------------------------------------

class TestTaskPlanner:
    def setup_method(self):
        from services.task_planner import ALLOWED_TASK_TOOLS, _normalize_tool, _tool_catalog_text
        self.ALLOWED_TASK_TOOLS = ALLOWED_TASK_TOOLS
        self._normalize_tool = _normalize_tool
        self._tool_catalog_text = _tool_catalog_text

    def test_canva_tools_in_allowed_list(self):
        assert "create_design" in self.ALLOWED_TASK_TOOLS
        assert "list_designs" in self.ALLOWED_TASK_TOOLS
        assert "get_design" in self.ALLOWED_TASK_TOOLS
        assert "export_design" in self.ALLOWED_TASK_TOOLS

    def test_canva_alias_canva_create(self):
        assert self._normalize_tool("canva_create") == "create_design"

    def test_canva_alias_design(self):
        assert self._normalize_tool("design") == "create_design"

    def test_canva_alias_export(self):
        assert self._normalize_tool("export") == "export_design"

    def test_canva_alias_canva_list(self):
        assert self._normalize_tool("canva_list") == "list_designs"

    def test_canva_alias_canva_get(self):
        assert self._normalize_tool("canva_get") == "get_design"

    def test_canva_catalog_section_present(self):
        catalog = self._tool_catalog_text()
        assert "Canva" in catalog
        assert "create_design" in catalog
        assert "list_designs" in catalog
        assert "get_design" in catalog
        assert "export_design" in catalog

    def test_canva_catalog_includes_presets(self):
        catalog = self._tool_catalog_text()
        assert "instagram_post" in catalog
        assert "presentation" in catalog

    def test_canva_catalog_includes_formats(self):
        catalog = self._tool_catalog_text()
        assert "png" in catalog
        assert "pdf" in catalog

    def test_existing_tools_unaffected(self):
        """Ensure Canva additions didn't break existing tool registration."""
        assert "web_search" in self.ALLOWED_TASK_TOOLS
        assert "smart_search_extract" in self.ALLOWED_TASK_TOOLS
        assert "execute_sql_query_tool" in self.ALLOWED_TASK_TOOLS
        assert "get_youtube_transcript" in self.ALLOWED_TASK_TOOLS
        assert "llm.generate" in self.ALLOWED_TASK_TOOLS

    def test_mcp_config_canva_tools_in_whitelist(self):
        """Canva MCP required_tools all appear in ALLOWED_TASK_TOOLS."""
        from services.mcp_service import app_state
        from core.config import CANVA_SERVICE_NAME
        required = app_state.mcp_configs[CANVA_SERVICE_NAME].required_tools
        for tool in required:
            assert tool in self.ALLOWED_TASK_TOOLS, f"Canva tool '{tool}' missing from ALLOWED_TASK_TOOLS"
