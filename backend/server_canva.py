"""
Canva MCP Server

Provides tools for creating, listing, retrieving, and exporting Canva designs
via the Canva Connect API.
"""
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv, find_dotenv
from fastmcp import FastMCP

# ---- Logging setup (stderr, same pattern as other MCP servers) ----
script_logger = logging.getLogger("server_canva")
script_logger.setLevel(logging.INFO)
if not script_logger.hasHandlers():
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - [SERVER_CANVA] %(message)s")
    )
    script_logger.addHandler(_handler)
    script_logger.propagate = False

# ---- Environment ----
dotenv_path = find_dotenv(usecwd=False, raise_error_if_not_found=False)
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

CANVA_API_TOKEN = os.getenv("CANVA_API_TOKEN")
if not CANVA_API_TOKEN:
    script_logger.critical("CANVA_API_TOKEN environment variable is not set.")
    raise ValueError("CANVA_API_TOKEN environment variable not set. Add it to your .env file.")

script_logger.info("CANVA_API_TOKEN loaded successfully.")

# ---- FastMCP server ----
mcp = FastMCP(
    name="CanvaServer",
    version="0.1.0",
    instructions="Provides Canva design creation, listing, retrieval, and export tools via the Canva Connect API.",
)

script_logger.info("FastMCP CanvaServer instance created.")

# Import after env is loaded so CANVA_BASE_URL override is respected
from utils.canva_client import (  # noqa: E402
    CanvaAPIError,
    CreateDesignRequest,
    DesignPreset,
    DesignSize,
    DesignUnit,
    ExportDesignRequest,
    ExportFormat,
    CanvaClient,
)


def _make_client() -> CanvaClient:
    return CanvaClient(api_token=CANVA_API_TOKEN)


@mcp.tool()
async def create_design(
    title: str,
    preset: str = "presentation",
    width: Optional[int] = None,
    height: Optional[int] = None,
    unit: str = "px",
    template_id: Optional[str] = None,
    brand_template_id: Optional[str] = None,
) -> dict:
    """
    Create a new Canva design.

    Use a standard preset (e.g. 'instagram_post', 'presentation', 'a4', 'youtube_thumbnail')
    or pass width + height + unit for a custom size. Optionally base it on an existing
    template or brand template (autofill).

    Args:
        title: Design title (required)
        preset: Size preset name. One of: instagram_post, instagram_story, facebook_post,
                facebook_cover, twitter_post, linkedin_banner, youtube_thumbnail,
                presentation, a4, a3, us_letter, custom. Default: presentation.
        width: Custom width (required when preset='custom')
        height: Custom height (required when preset='custom')
        unit: Dimension unit for custom size: px, mm, in, pt. Default: px
        template_id: Optional Canva template ID to base the design on
        brand_template_id: Optional brand template ID (triggers Autofill workflow)

    Returns:
        dict with design id, title, url, thumbnail_url, width, height, created_at
    """
    try:
        preset_enum = DesignPreset(preset.lower())
    except ValueError:
        return {"status": "error", "message": f"Invalid preset '{preset}'. Valid values: {[p.value for p in DesignPreset]}"}

    size = None
    if preset_enum == DesignPreset.CUSTOM:
        if not width or not height:
            return {"status": "error", "message": "width and height are required when preset='custom'"}
        try:
            unit_enum = DesignUnit(unit.lower())
        except ValueError:
            return {"status": "error", "message": f"Invalid unit '{unit}'. Valid values: px, mm, in, pt"}
        size = DesignSize(width=width, height=height, unit=unit_enum)

    try:
        request = CreateDesignRequest(
            title=title,
            preset=preset_enum,
            size=size,
            template_id=template_id,
            brand_template_id=brand_template_id,
        )
    except Exception as e:
        return {"status": "error", "message": str(e)}

    try:
        async with _make_client() as client:
            design = await client.create_design(request)
            script_logger.info(f"Design created: {design.get('id')} - {design.get('title')}")
            return {"status": "success", **design}
    except CanvaAPIError as e:
        script_logger.error(f"Canva API error in create_design: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in create_design: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def list_designs(
    page_token: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """
    List designs in the authenticated Canva account.

    Returns paginated results. Use the next_page_token from the response
    to fetch additional pages.

    Args:
        page_token: Optional pagination token from a previous response
        limit: Maximum designs to return (default 50, max 100)

    Returns:
        dict with items (list of designs), next_page_token, total_count
    """
    try:
        async with _make_client() as client:
            result = await client.list_designs(page_token=page_token, limit=limit)
            script_logger.info(f"Listed {len(result.get('items', []))} designs")
            return {"status": "success", **result}
    except CanvaAPIError as e:
        script_logger.error(f"Canva API error in list_designs: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in list_designs: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def get_design(design_id: str) -> dict:
    """
    Retrieve detailed information about a specific Canva design.

    Args:
        design_id: The Canva design ID

    Returns:
        dict with design id, title, url, thumbnail_url, width, height, created_at, etc.
    """
    if not design_id:
        return {"status": "error", "message": "design_id is required"}
    try:
        async with _make_client() as client:
            design = await client.get_design(design_id)
            script_logger.info(f"Retrieved design: {design_id}")
            return {"status": "success", **design}
    except CanvaAPIError as e:
        script_logger.error(f"Canva API error in get_design: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in get_design: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def export_design(
    design_id: str,
    format: str = "png",
    width: Optional[int] = None,
    height: Optional[int] = None,
    quality: Optional[int] = None,
    pages: Optional[str] = None,
) -> dict:
    """
    Export a Canva design to a downloadable file.

    Submits an export job and polls until completion (or timeout). Returns a
    download_url when the export is successful.

    Args:
        design_id: The Canva design ID to export
        format: Export format — png, jpg, pdf, svg, mp4, gif. Default: png
        width: Optional output width in pixels (aspect ratio preserved if height omitted)
        height: Optional output height in pixels
        quality: JPG quality 1-100 (only for jpg/jpeg format)
        pages: Comma-separated page numbers to export for multi-page designs, e.g. "1,2,3"

    Returns:
        dict with status, job_id, download_url, file_size_bytes
    """
    if not design_id:
        return {"status": "error", "message": "design_id is required"}

    try:
        fmt_enum = ExportFormat(format.lower())
    except ValueError:
        return {"status": "error", "message": f"Invalid format '{format}'. Valid values: {[f.value for f in ExportFormat]}"}

    page_list = None
    if pages:
        try:
            page_list = [int(p.strip()) for p in pages.split(",") if p.strip()]
        except ValueError:
            return {"status": "error", "message": "pages must be comma-separated integers, e.g. '1,2,3'"}

    try:
        request = ExportDesignRequest(
            design_id=design_id,
            format=fmt_enum,
            width=width,
            height=height,
            quality=quality,
            pages=page_list,
        )
    except Exception as e:
        return {"status": "error", "message": str(e)}

    try:
        async with _make_client() as client:
            result = await client.export_design(request)
            script_logger.info(f"Export job {result.get('job_id')} status={result.get('status')}")
            return {"status": "success", **result}
    except CanvaAPIError as e:
        script_logger.error(f"Canva API error in export_design: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in export_design: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
