"""
Tests for the Figma MCP server integration.

Covers:
- Pydantic model validation (no API calls)
- FigmaClient methods with mocked httpx responses
- server_figma tool functions with mocked FigmaClient
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

def _load_server_figma():
    """Load server_figma.py with a fake token so the import doesn't raise."""
    os.environ.setdefault("FIGMA_ACCESS_TOKEN", "test_fake_figma_token_for_testing")
    spec = importlib.util.spec_from_file_location(
        "server_figma_test",
        str(BACKEND_DIR / "server_figma.py"),
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


# ---------------------------------------------------------------------------
# Sample API responses
# ---------------------------------------------------------------------------

SAMPLE_FILE_RESPONSE = {
    "name": "My Design File",
    "lastModified": "2024-01-15T10:00:00Z",
    "version": "123456789",
    "document": {
        "id": "0:0",
        "name": "Document",
        "type": "DOCUMENT",
        "children": [
            {
                "id": "0:1",
                "name": "Page 1",
                "type": "CANVAS",
                "children": [
                    {
                        "id": "1:2",
                        "name": "Hero Frame",
                        "type": "FRAME",
                        "width": 1440.0,
                        "height": 900.0,
                    }
                ],
            }
        ],
    },
}

SAMPLE_FILE_NODES_RESPONSE = {
    "name": "My Design File",
    "lastModified": "2024-01-15T10:00:00Z",
    "version": "123456789",
    "nodes": {
        "1:2": {
            "id": "1:2",
            "name": "Hero Frame",
            "type": "FRAME",
            "width": 1440.0,
            "height": 900.0,
        }
    },
}

SAMPLE_IMAGE_RESPONSE = {
    "err": None,
    "images": {
        "1:2": "https://figma-alpha-api.s3.us-west-2.amazonaws.com/img/node1.png",
        "3:4": "https://figma-alpha-api.s3.us-west-2.amazonaws.com/img/node2.png",
    },
}

SAMPLE_COMMENTS_RESPONSE = {
    "comments": [
        {
            "id": "comment_001",
            "message": "Looks great!",
            "file_key": "ABC123",
        },
        {
            "id": "comment_002",
            "message": "Please adjust the spacing.",
            "file_key": "ABC123",
        },
    ]
}

SAMPLE_COMMENT_POST_RESPONSE = {
    "id": "comment_003",
    "message": "Added a new comment",
    "file_key": "ABC123",
}

SAMPLE_DESIGN_SYSTEM_RESPONSE = {
    "name": "Design System File",
    "lastModified": "2024-01-15T10:00:00Z",
    "version": "999",
    "document": {
        "id": "0:0",
        "name": "Document",
        "type": "DOCUMENT",
        "children": [
            {
                "id": "0:1",
                "name": "Page 1",
                "type": "CANVAS",
                "children": [
                    {
                        "id": "1:1",
                        "name": "Primary Button",
                        "type": "FRAME",
                        "fills": [
                            {
                                "type": "SOLID",
                                "color": {"r": 0.2, "g": 0.4, "b": 0.8, "a": 1.0},
                            }
                        ],
                    }
                ],
            }
        ],
    },
    "styles": {
        "S:abc123": {
            "key": "S:abc123",
            "name": "Primary Blue",
            "styleType": "FILL",
        }
    },
    "components": {
        "C:btn001": {
            "key": "C:btn001",
            "name": "Button/Primary",
        }
    },
}


# ---------------------------------------------------------------------------
# 1. Pydantic model validation
# ---------------------------------------------------------------------------

class TestModels:
    """Pydantic model validation — no network calls."""

    def setup_method(self):
        from utils.figma_client import (
            Color,
            ComponentMetadata,
            DesignSystem,
            DesignToken,
            ExportFormat,
            FigmaAPIError,
            Node,
            NodeType,
            Paint,
            PaintType,
        )
        self.Color = Color
        self.ComponentMetadata = ComponentMetadata
        self.DesignSystem = DesignSystem
        self.DesignToken = DesignToken
        self.ExportFormat = ExportFormat
        self.FigmaAPIError = FigmaAPIError
        self.Node = Node
        self.NodeType = NodeType
        self.Paint = Paint
        self.PaintType = PaintType

    def test_node_type_enum_values(self):
        assert self.NodeType.DOCUMENT == "DOCUMENT"
        assert self.NodeType.FRAME == "FRAME"
        assert self.NodeType.TEXT == "TEXT"
        assert self.NodeType.COMPONENT == "COMPONENT"

    def test_paint_type_enum_values(self):
        assert self.PaintType.SOLID == "SOLID"
        assert self.PaintType.GRADIENT_LINEAR == "GRADIENT_LINEAR"
        assert self.PaintType.IMAGE == "IMAGE"

    def test_export_format_enum_values(self):
        assert self.ExportFormat.PNG == "png"
        assert self.ExportFormat.JPG == "jpg"
        assert self.ExportFormat.SVG == "svg"
        assert self.ExportFormat.PDF == "pdf"

    def test_color_validation_valid(self):
        color = self.Color(r=0.5, g=0.3, b=0.8, a=1.0)
        assert color.r == 0.5
        assert color.a == 1.0

    def test_color_validation_invalid_range(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.Color(r=1.5, g=0.0, b=0.0, a=1.0)  # r > 1

    def test_node_model_basic(self):
        node = self.Node(id="1:1", name="My Frame", type=self.NodeType.FRAME)
        assert node.id == "1:1"
        assert node.name == "My Frame"
        assert node.type == self.NodeType.FRAME
        assert node.children is None

    def test_node_model_with_children(self):
        child = self.Node(id="1:2", name="Child", type=self.NodeType.RECTANGLE)
        parent = self.Node(id="1:1", name="Parent", type=self.NodeType.FRAME, children=[child])
        assert len(parent.children) == 1
        assert parent.children[0].id == "1:2"

    def test_design_token_model(self):
        token = self.DesignToken(name="primary-color", type="color", value="S:abc123")
        assert token.name == "primary-color"
        assert token.type == "color"
        assert token.value == "S:abc123"

    def test_figma_api_error_attributes(self):
        err = self.FigmaAPIError(
            message="File not found",
            status_code=404,
            error_code="FILE_NOT_FOUND",
        )
        assert err.message == "File not found"
        assert err.status_code == 404
        assert err.error_code == "FILE_NOT_FOUND"
        assert str(err) == "File not found"


# ---------------------------------------------------------------------------
# 2. FigmaClient with mocked httpx
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_get_file():
    from utils.figma_client import FigmaClient
    client = FigmaClient(token="fake_token")
    client._rate_limit = AsyncMock()
    client.client.get = AsyncMock(return_value=_make_mock_response(SAMPLE_FILE_RESPONSE))

    result = await client.get_file("ABC123", depth=3)

    assert result["name"] == "My Design File"
    assert result["version"] == "123456789"
    assert result["document"]["id"] == "0:0"
    client.client.get.assert_called_once()
    call_kwargs = client.client.get.call_args
    assert "/files/ABC123" in str(call_kwargs)
    await client.close()


@pytest.mark.asyncio
async def test_client_get_file_nodes():
    from utils.figma_client import FigmaClient
    client = FigmaClient(token="fake_token")
    client._rate_limit = AsyncMock()
    client.client.get = AsyncMock(return_value=_make_mock_response(SAMPLE_FILE_NODES_RESPONSE))

    result = await client.get_file_nodes("ABC123", ["1:2", "3:4"])

    assert result["name"] == "My Design File"
    assert "1:2" in result["nodes"]
    # Verify ids were joined and passed
    call_kwargs = client.client.get.call_args
    assert "1:2,3:4" in str(call_kwargs)
    await client.close()


@pytest.mark.asyncio
async def test_client_get_images():
    from utils.figma_client import FigmaClient
    client = FigmaClient(token="fake_token")
    client._rate_limit = AsyncMock()
    client.client.get = AsyncMock(return_value=_make_mock_response(SAMPLE_IMAGE_RESPONSE))

    result = await client.get_images("ABC123", ["1:2", "3:4"], format="png", scale=2.0)

    assert result["images"]["1:2"].endswith("node1.png")
    assert result["err"] is None
    await client.close()


@pytest.mark.asyncio
async def test_client_get_comments():
    from utils.figma_client import FigmaClient
    client = FigmaClient(token="fake_token")
    client._rate_limit = AsyncMock()
    client.client.get = AsyncMock(return_value=_make_mock_response(SAMPLE_COMMENTS_RESPONSE))

    result = await client.get_comments("ABC123")

    assert len(result["comments"]) == 2
    assert result["comments"][0]["id"] == "comment_001"
    assert result["comments"][0]["message"] == "Looks great!"
    await client.close()


@pytest.mark.asyncio
async def test_client_post_comment():
    from utils.figma_client import FigmaClient
    client = FigmaClient(token="fake_token")
    client._rate_limit = AsyncMock()
    client.client.post = AsyncMock(return_value=_make_mock_response(SAMPLE_COMMENT_POST_RESPONSE))

    result = await client.post_comment("ABC123", "Added a new comment", node_id="1:2")

    assert result["id"] == "comment_003"
    assert result["message"] == "Added a new comment"
    assert result["file_key"] == "ABC123"
    call_kwargs = client.client.post.call_args
    payload = call_kwargs[1]["json"]
    assert payload["message"] == "Added a new comment"
    assert payload["client_meta"]["node_id"] == "1:2"
    await client.close()


@pytest.mark.asyncio
async def test_client_get_design_system():
    from utils.figma_client import FigmaClient
    client = FigmaClient(token="fake_token")
    client._rate_limit = AsyncMock()
    client.client.get = AsyncMock(return_value=_make_mock_response(SAMPLE_DESIGN_SYSTEM_RESPONSE))

    result = await client.get_design_system("ABC123")

    assert result["name"] == "Design System File"
    assert result["file_key"] == "ABC123"
    # Should have extracted the solid fill as a color token
    assert len(result["colors"]) >= 1
    # Should have extracted the style token (FILL type → "fill" not "color")
    assert len(result["components"]) == 1
    assert result["components"][0]["name"] == "Button/Primary"
    await client.close()


@pytest.mark.asyncio
async def test_client_api_error_propagates():
    from utils.figma_client import FigmaClient, FigmaAPIError
    client = FigmaClient(token="fake_token")
    client._rate_limit = AsyncMock()
    error_response = _make_error_response(403, {"err": "FORBIDDEN", "message": "Access denied"})
    client.client.get = AsyncMock(return_value=error_response)

    with pytest.raises(FigmaAPIError) as exc_info:
        await client.get_file("RESTRICTED_FILE")

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "FORBIDDEN"
    await client.close()


# ---------------------------------------------------------------------------
# 3. server_figma tool functions
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def server_mod():
    """Load server_figma module once for all tool tests."""
    return _load_server_figma()


@pytest.mark.asyncio
async def test_tool_figma_get_file_success(server_mod):
    mock_result = {
        "name": "My Design File",
        "lastModified": "2024-01-15T10:00:00Z",
        "version": "123456789",
        "document": {"id": "0:0", "name": "Document", "type": "DOCUMENT"},
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_file = AsyncMock(return_value=mock_result)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.figma_get_file("ABC123", depth=3)

    assert result["status"] == "success"
    assert result["name"] == "My Design File"
    assert result["version"] == "123456789"
    mock_client.get_file.assert_called_once_with("ABC123", depth=3)


@pytest.mark.asyncio
async def test_tool_figma_get_file_missing_key(server_mod):
    result = await server_mod.figma_get_file("")
    assert result["status"] == "error"
    assert "file_key is required" in result["message"]


@pytest.mark.asyncio
async def test_tool_figma_get_file_api_error(server_mod):
    from utils.figma_client import FigmaAPIError
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_file = AsyncMock(
        side_effect=FigmaAPIError("Not found", status_code=404, error_code="FILE_NOT_FOUND")
    )

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.figma_get_file("MISSING_FILE")

    assert result["status"] == "error"
    assert "Not found" in result["message"]
    assert result["error_code"] == "FILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_tool_figma_get_nodes_success(server_mod):
    mock_result = {
        "name": "My File",
        "version": "1",
        "nodes": {"1:2": {"id": "1:2", "name": "Frame"}},
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_file_nodes = AsyncMock(return_value=mock_result)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.figma_get_nodes("ABC123", "1:2, 3:4")

    assert result["status"] == "success"
    assert "1:2" in result["nodes"]
    # Verify node IDs were parsed and stripped
    call_args = mock_client.get_file_nodes.call_args
    assert call_args[0][1] == ["1:2", "3:4"]


@pytest.mark.asyncio
async def test_tool_figma_get_nodes_empty_ids(server_mod):
    result = await server_mod.figma_get_nodes("ABC123", "   ,  ,  ")
    assert result["status"] == "error"
    assert "at least one valid ID" in result["message"]


@pytest.mark.asyncio
async def test_tool_figma_export_images_success(server_mod):
    mock_result = {
        "err": None,
        "images": {"1:2": "https://s3.amazonaws.com/img/node.png"},
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_images = AsyncMock(return_value=mock_result)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.figma_export_images("ABC123", "1:2", format="png", scale=2.0)

    assert result["status"] == "success"
    assert "1:2" in result["images"]


@pytest.mark.asyncio
async def test_tool_figma_export_images_invalid_format(server_mod):
    result = await server_mod.figma_export_images("ABC123", "1:2", format="bmp")
    assert result["status"] == "error"
    assert "Invalid format" in result["message"]


@pytest.mark.asyncio
async def test_tool_figma_export_images_invalid_scale(server_mod):
    result = await server_mod.figma_export_images("ABC123", "1:2", scale=10.0)
    assert result["status"] == "error"
    assert "scale must be between" in result["message"]


@pytest.mark.asyncio
async def test_tool_figma_get_comments_success(server_mod):
    mock_result = {
        "comments": [
            {"id": "c1", "message": "Nice work!", "file_key": "ABC123"},
        ]
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_comments = AsyncMock(return_value=mock_result)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.figma_get_comments("ABC123")

    assert result["status"] == "success"
    assert len(result["comments"]) == 1
    assert result["comments"][0]["id"] == "c1"


@pytest.mark.asyncio
async def test_tool_figma_post_comment_success(server_mod):
    mock_result = {"id": "c99", "message": "Hello", "file_key": "ABC123"}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post_comment = AsyncMock(return_value=mock_result)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.figma_post_comment("ABC123", "Hello", node_id="1:2")

    assert result["status"] == "success"
    assert result["id"] == "c99"
    mock_client.post_comment.assert_called_once_with("ABC123", "Hello", node_id="1:2", parent_id=None)


@pytest.mark.asyncio
async def test_tool_figma_post_comment_missing_message(server_mod):
    result = await server_mod.figma_post_comment("ABC123", "")
    assert result["status"] == "error"
    assert "message is required" in result["message"]


@pytest.mark.asyncio
async def test_tool_figma_get_design_system_success(server_mod):
    mock_result = {
        "file_key": "ABC123",
        "name": "Design System",
        "colors": [{"name": "primary-fill-0", "type": "color", "value": {"r": 0.2, "g": 0.4, "b": 0.8, "a": 1.0}}],
        "typography": [],
        "spacing": [],
        "effects": [],
        "components": [{"key": "C:001", "name": "Button"}],
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_design_system = AsyncMock(return_value=mock_result)

    with patch.object(server_mod, "_make_client", return_value=mock_client):
        result = await server_mod.figma_get_design_system("ABC123")

    assert result["status"] == "success"
    assert result["name"] == "Design System"
    assert len(result["colors"]) == 1
    assert len(result["components"]) == 1


# ---------------------------------------------------------------------------
# 4. Task runner routing
# ---------------------------------------------------------------------------

class TestTaskRunnerRouting:
    def setup_method(self):
        from services.task_runner import _resolve_tool
        from core.config import FIGMA_SERVICE_NAME, CANVA_SERVICE_NAME, WEB_SEARCH_SERVICE_NAME
        self._resolve_tool = _resolve_tool
        self.FIGMA_SERVICE_NAME = FIGMA_SERVICE_NAME
        self.CANVA_SERVICE_NAME = CANVA_SERVICE_NAME
        self.WEB_SEARCH_SERVICE_NAME = WEB_SEARCH_SERVICE_NAME

    def test_figma_get_file_routes_to_figma(self):
        svc, tool = self._resolve_tool("figma_get_file")
        assert svc == self.FIGMA_SERVICE_NAME
        assert tool == "figma_get_file"

    def test_figma_get_nodes_routes_to_figma(self):
        svc, tool = self._resolve_tool("figma_get_nodes")
        assert svc == self.FIGMA_SERVICE_NAME
        assert tool == "figma_get_nodes"

    def test_figma_export_images_routes_to_figma(self):
        svc, tool = self._resolve_tool("figma_export_images")
        assert svc == self.FIGMA_SERVICE_NAME
        assert tool == "figma_export_images"

    def test_figma_get_comments_routes_to_figma(self):
        svc, tool = self._resolve_tool("figma_get_comments")
        assert svc == self.FIGMA_SERVICE_NAME
        assert tool == "figma_get_comments"

    def test_figma_post_comment_routes_to_figma(self):
        svc, tool = self._resolve_tool("figma_post_comment")
        assert svc == self.FIGMA_SERVICE_NAME
        assert tool == "figma_post_comment"

    def test_figma_get_design_system_routes_to_figma(self):
        svc, tool = self._resolve_tool("figma_get_design_system")
        assert svc == self.FIGMA_SERVICE_NAME
        assert tool == "figma_get_design_system"

    def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            self._resolve_tool("figma_magic_nonexistent_tool")

    def test_canva_tools_still_route_correctly(self):
        svc, tool = self._resolve_tool("create_design")
        assert svc == self.CANVA_SERVICE_NAME

    def test_web_search_still_routes_correctly(self):
        svc, tool = self._resolve_tool("web_search")
        assert svc == self.WEB_SEARCH_SERVICE_NAME


# ---------------------------------------------------------------------------
# 5. MCP service registry
# ---------------------------------------------------------------------------

class TestMCPServiceRegistry:
    def setup_method(self):
        from services.mcp_service import app_state
        from core.config import FIGMA_SERVICE_NAME
        self.app_state = app_state
        self.FIGMA_SERVICE_NAME = FIGMA_SERVICE_NAME

    def test_figma_service_registered(self):
        assert self.FIGMA_SERVICE_NAME in self.app_state.mcp_configs

    def test_figma_service_script_name(self):
        config = self.app_state.mcp_configs[self.FIGMA_SERVICE_NAME]
        assert config.script_name == "server_figma.py"

    def test_figma_required_tools(self):
        config = self.app_state.mcp_configs[self.FIGMA_SERVICE_NAME]
        expected = ["figma_get_file", "figma_get_nodes", "figma_export_images",
                    "figma_get_comments", "figma_post_comment", "figma_get_design_system"]
        for tool in expected:
            assert tool in config.required_tools, f"'{tool}' missing from required_tools"

    def test_figma_service_name_constant(self):
        from core.config import FIGMA_SERVICE_NAME
        assert FIGMA_SERVICE_NAME == "figma_service"

    def test_canva_service_still_registered(self):
        from core.config import CANVA_SERVICE_NAME
        assert CANVA_SERVICE_NAME in self.app_state.mcp_configs


# ---------------------------------------------------------------------------
# 6. Task planner — allowed tools, aliases, catalog
# ---------------------------------------------------------------------------

class TestTaskPlanner:
    def setup_method(self):
        from services.task_planner import ALLOWED_TASK_TOOLS, _normalize_tool, _tool_catalog_text
        self.ALLOWED_TASK_TOOLS = ALLOWED_TASK_TOOLS
        self._normalize_tool = _normalize_tool
        self._tool_catalog_text = _tool_catalog_text

    def test_figma_tools_in_allowed_list(self):
        for tool in ["figma_get_file", "figma_get_nodes", "figma_export_images",
                     "figma_get_comments", "figma_post_comment", "figma_get_design_system"]:
            assert tool in self.ALLOWED_TASK_TOOLS, f"'{tool}' missing from ALLOWED_TASK_TOOLS"

    def test_alias_figma_file(self):
        assert self._normalize_tool("figma_file") == "figma_get_file"

    def test_alias_figma_nodes(self):
        assert self._normalize_tool("figma_nodes") == "figma_get_nodes"

    def test_alias_figma_images(self):
        assert self._normalize_tool("figma_images") == "figma_export_images"

    def test_alias_figma_comments(self):
        assert self._normalize_tool("figma_comments") == "figma_get_comments"

    def test_alias_figma_comment(self):
        assert self._normalize_tool("figma_comment") == "figma_post_comment"

    def test_alias_figma_design_system(self):
        assert self._normalize_tool("figma_design_system") == "figma_get_design_system"

    def test_alias_figma_tokens(self):
        assert self._normalize_tool("figma_tokens") == "figma_get_design_system"

    def test_figma_catalog_section_present(self):
        catalog = self._tool_catalog_text()
        assert "Figma" in catalog
        assert "figma_get_file" in catalog
        assert "figma_get_nodes" in catalog
        assert "figma_export_images" in catalog
        assert "figma_get_comments" in catalog
        assert "figma_post_comment" in catalog
        assert "figma_get_design_system" in catalog

    def test_figma_catalog_includes_formats(self):
        catalog = self._tool_catalog_text()
        assert "png" in catalog
        assert "svg" in catalog
        assert "file_key" in catalog

    def test_existing_tools_unaffected(self):
        """Ensure Figma additions didn't break existing tool registration."""
        for tool in ["web_search", "smart_search_extract", "execute_sql_query_tool",
                     "get_youtube_transcript", "create_design", "llm.generate"]:
            assert tool in self.ALLOWED_TASK_TOOLS, f"Existing tool '{tool}' was broken"

    def test_mcp_config_figma_tools_in_whitelist(self):
        """Figma MCP required_tools all appear in ALLOWED_TASK_TOOLS."""
        from services.mcp_service import app_state
        from core.config import FIGMA_SERVICE_NAME
        required = app_state.mcp_configs[FIGMA_SERVICE_NAME].required_tools
        for tool in required:
            assert tool in self.ALLOWED_TASK_TOOLS, f"Figma tool '{tool}' missing from ALLOWED_TASK_TOOLS"
