"""
Figma MCP Server

Provides tools for reading Figma files, extracting nodes, exporting images,
managing comments, and extracting design tokens via the Figma REST API.
"""
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv, find_dotenv
from fastmcp import FastMCP

# ---- Logging setup (stderr, same pattern as other MCP servers) ----
script_logger = logging.getLogger("server_figma")
script_logger.setLevel(logging.INFO)
if not script_logger.hasHandlers():
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - [SERVER_FIGMA] %(message)s")
    )
    script_logger.addHandler(_handler)
    script_logger.propagate = False

# ---- Environment ----
dotenv_path = find_dotenv(usecwd=False, raise_error_if_not_found=False)
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

FIGMA_ACCESS_TOKEN = os.getenv("FIGMA_ACCESS_TOKEN")
if not FIGMA_ACCESS_TOKEN:
    script_logger.critical("FIGMA_ACCESS_TOKEN environment variable is not set.")
    raise ValueError("FIGMA_ACCESS_TOKEN environment variable not set. Add it to your .env file.")

script_logger.info("FIGMA_ACCESS_TOKEN loaded successfully.")

# ---- FastMCP server ----
mcp = FastMCP(
    name="FigmaServer",
    version="0.1.0",
    instructions="Provides Figma file reading, node extraction, image export, comment management, and design system tools via the Figma REST API.",
)

script_logger.info("FastMCP FigmaServer instance created.")

# Import after env is loaded so FIGMA_BASE_URL override is respected
from utils.figma_client import (  # noqa: E402
    ExportFormat,
    FigmaAPIError,
    FigmaClient,
)


def _make_client() -> FigmaClient:
    return FigmaClient(token=FIGMA_ACCESS_TOKEN)


@mcp.tool()
async def figma_get_file(
    file_key: str,
    depth: int = 3,
) -> dict:
    """
    Get the structure and metadata of a Figma file.

    The file_key is found in the Figma file URL:
    figma.com/file/{file_key}/...

    Args:
        file_key: Figma file key from the URL
        depth: Depth of node tree to retrieve (1-4 recommended, default 3)

    Returns:
        dict with name, lastModified, version, document (node tree), components, styles
    """
    if not file_key:
        return {"status": "error", "message": "file_key is required"}
    try:
        async with _make_client() as client:
            result = await client.get_file(file_key, depth=depth)
            script_logger.info(f"Retrieved Figma file: {file_key}")
            return {"status": "success", **result}
    except FigmaAPIError as e:
        script_logger.error(f"Figma API error in figma_get_file: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in figma_get_file: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def figma_get_nodes(
    file_key: str,
    node_ids: str,
    depth: Optional[int] = None,
) -> dict:
    """
    Get specific nodes from a Figma file by their IDs.

    Args:
        file_key: Figma file key from the URL
        node_ids: Comma-separated node IDs to retrieve, e.g. "1:2,3:4,5:6"
        depth: Optional depth of node subtree to retrieve

    Returns:
        dict with name, version, nodes (map of node_id -> node data)
    """
    if not file_key:
        return {"status": "error", "message": "file_key is required"}
    if not node_ids:
        return {"status": "error", "message": "node_ids is required"}
    node_id_list = [n.strip() for n in node_ids.split(",") if n.strip()]
    if not node_id_list:
        return {"status": "error", "message": "node_ids must contain at least one valid ID"}
    try:
        async with _make_client() as client:
            result = await client.get_file_nodes(file_key, node_id_list, depth=depth)
            script_logger.info(f"Retrieved {len(node_id_list)} nodes from {file_key}")
            return {"status": "success", **result}
    except FigmaAPIError as e:
        script_logger.error(f"Figma API error in figma_get_nodes: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in figma_get_nodes: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def figma_export_images(
    file_key: str,
    node_ids: str,
    format: str = "png",
    scale: float = 1.0,
) -> dict:
    """
    Export Figma nodes as images, returning download URLs.

    The returned URLs are temporary (expire after a short time). Download them promptly.

    Args:
        file_key: Figma file key from the URL
        node_ids: Comma-separated node IDs to export, e.g. "1:2,3:4"
        format: Export format — png, jpg, svg, pdf. Default: png
        scale: Export scale multiplier (0.01 to 4). Default: 1.0

    Returns:
        dict with images (map of node_id -> URL) and any error
    """
    if not file_key:
        return {"status": "error", "message": "file_key is required"}
    if not node_ids:
        return {"status": "error", "message": "node_ids is required"}
    node_id_list = [n.strip() for n in node_ids.split(",") if n.strip()]
    if not node_id_list:
        return {"status": "error", "message": "node_ids must contain at least one valid ID"}

    try:
        fmt_enum = ExportFormat(format.lower())
    except ValueError:
        return {"status": "error", "message": f"Invalid format '{format}'. Valid values: {[f.value for f in ExportFormat]}"}

    if not (0.01 <= scale <= 4.0):
        return {"status": "error", "message": "scale must be between 0.01 and 4.0"}

    try:
        async with _make_client() as client:
            result = await client.get_images(file_key, node_id_list, format=fmt_enum.value, scale=scale)
            script_logger.info(f"Exported {len(node_id_list)} nodes from {file_key} as {format}")
            return {"status": "success", **result}
    except FigmaAPIError as e:
        script_logger.error(f"Figma API error in figma_export_images: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in figma_export_images: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def figma_get_comments(file_key: str) -> dict:
    """
    Get all comments on a Figma file.

    Args:
        file_key: Figma file key from the URL

    Returns:
        dict with comments list (each with id, message, user, created_at, node anchor)
    """
    if not file_key:
        return {"status": "error", "message": "file_key is required"}
    try:
        async with _make_client() as client:
            result = await client.get_comments(file_key)
            count = len(result.get("comments", []))
            script_logger.info(f"Retrieved {count} comments from {file_key}")
            return {"status": "success", **result}
    except FigmaAPIError as e:
        script_logger.error(f"Figma API error in figma_get_comments: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in figma_get_comments: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def figma_post_comment(
    file_key: str,
    message: str,
    node_id: Optional[str] = None,
    parent_id: Optional[str] = None,
) -> dict:
    """
    Post a comment to a Figma file.

    Args:
        file_key: Figma file key from the URL
        message: Comment text
        node_id: Optional node ID to anchor the comment to a specific element
        parent_id: Optional parent comment ID to reply to an existing comment

    Returns:
        dict with the created comment (id, message, user, created_at)
    """
    if not file_key:
        return {"status": "error", "message": "file_key is required"}
    if not message:
        return {"status": "error", "message": "message is required"}
    try:
        async with _make_client() as client:
            result = await client.post_comment(file_key, message, node_id=node_id, parent_id=parent_id)
            script_logger.info(f"Posted comment to {file_key}: {result.get('id')}")
            return {"status": "success", **result}
    except FigmaAPIError as e:
        script_logger.error(f"Figma API error in figma_post_comment: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in figma_post_comment: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def figma_get_design_system(file_key: str) -> dict:
    """
    Extract the design system (tokens, components) from a Figma file.

    Traverses the node tree to collect color tokens, typography tokens,
    spacing tokens, and component metadata. Also extracts named styles.

    Args:
        file_key: Figma file key from the URL

    Returns:
        dict with colors, typography, spacing, effects, and components lists
    """
    if not file_key:
        return {"status": "error", "message": "file_key is required"}
    try:
        async with _make_client() as client:
            result = await client.get_design_system(file_key)
            color_count = len(result.get("colors", []))
            comp_count = len(result.get("components", []))
            script_logger.info(f"Extracted design system from {file_key}: {color_count} colors, {comp_count} components")
            return {"status": "success", **result}
    except FigmaAPIError as e:
        script_logger.error(f"Figma API error in figma_get_design_system: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in figma_get_design_system: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
