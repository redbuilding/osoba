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
    AssetUploadRequest,
    CreateDesignRequest,
    DesignPreset,
    DesignSize,
    DesignUnit,
    ExportDesignRequest,
    ExportFormat,
    ImportDesignRequest,
    ResizeDesignRequest,
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
) -> dict:
    """
    Create a new Canva design.

    Use a standard preset (e.g. 'instagram_post', 'presentation', 'a4', 'youtube_thumbnail')
    or pass width + height + unit for a custom size. For brand template autofill, use
    the autofill_design tool instead.

    Args:
        title: Design title (required)
        preset: Size preset name. One of: instagram_post, instagram_story, facebook_post,
                facebook_cover, twitter_post, linkedin_banner, youtube_thumbnail,
                presentation, a4, a3, us_letter, custom. Default: presentation.
        width: Custom width (required when preset='custom')
        height: Custom height (required when preset='custom')
        unit: Dimension unit for custom size: px, mm, in, pt. Default: px
        template_id: Optional Canva template ID to base the design on

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


@mcp.tool()
async def upload_asset(name: str, url: str) -> dict:
    """
    Upload an image or video to the user's Canva asset library from a URL.

    The URL must be publicly accessible. Supported: JPEG, PNG, HEIC, GIF, TIFF,
    WEBP images (max 50MB) and M4V, MKV, MP4, MPEG, MOV, WebM videos (max 100MB via URL).

    Args:
        name: A name for the asset (1-255 chars)
        url: Public URL of the image or video file

    Returns:
        dict with asset_id, name, type, thumbnail_url
    """
    try:
        request = AssetUploadRequest(name=name, url=url)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    try:
        async with _make_client() as client:
            result = await client.upload_asset_url(request)
            script_logger.info(f"Asset uploaded: {result.get('asset_id')}")
            return {"status": "success", **result}
    except CanvaAPIError as e:
        script_logger.error(f"Canva API error in upload_asset: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in upload_asset: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def autofill_design(
    brand_template_id: str,
    data: str,
    title: Optional[str] = None,
) -> dict:
    """
    Create a design by autofilling a brand template with data.

    First use get_brand_template_dataset to discover available fields, then pass
    field values as a JSON string. Requires Canva Enterprise.

    Args:
        brand_template_id: The brand template ID
        data: JSON string mapping field names to values, e.g.
              '{"HEADLINE": {"type": "text", "text": "Hello"},
                "PHOTO": {"type": "image", "asset_id": "Msd59349ff"}}'
        title: Optional title for the new design

    Returns:
        dict with design_id, url, thumbnail_url
    """
    import json as _json
    try:
        parsed_data = _json.loads(data)
    except (ValueError, TypeError):
        return {"status": "error", "message": "data must be a valid JSON string"}
    try:
        async with _make_client() as client:
            result = await client.create_autofill(brand_template_id, parsed_data, title=title)
            script_logger.info(f"Autofill design created: {result.get('design_id')}")
            return {"status": "success", **result}
    except CanvaAPIError as e:
        script_logger.error(f"Canva API error in autofill_design: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in autofill_design: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def get_brand_template_dataset(brand_template_id: str) -> dict:
    """
    Get the autofillable data fields from a brand template.

    Returns field names and their types (text, image, chart) so you know what
    data to pass to autofill_design. Requires Canva Enterprise.

    Args:
        brand_template_id: The brand template ID

    Returns:
        dict with dataset mapping field names to their types
    """
    if not brand_template_id:
        return {"status": "error", "message": "brand_template_id is required"}
    try:
        async with _make_client() as client:
            result = await client.get_brand_template_dataset(brand_template_id)
            script_logger.info(f"Retrieved dataset for template: {brand_template_id}")
            return {"status": "success", **result}
    except CanvaAPIError as e:
        script_logger.error(f"Canva API error in get_brand_template_dataset: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in get_brand_template_dataset: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def import_design(
    title: str,
    url: str,
    mime_type: Optional[str] = None,
) -> dict:
    """
    Import a file from a URL into Canva as an editable design.

    Supports PDF, PPTX, DOCX, PSD, AI, Keynote, and many more formats.
    The URL must be publicly accessible.

    Args:
        title: Title for the imported design
        url: Public URL of the file to import
        mime_type: Optional MIME type (auto-detected if omitted)

    Returns:
        dict with designs list (each with id, url, title, page_count)
    """
    try:
        request = ImportDesignRequest(title=title, url=url, mime_type=mime_type)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    try:
        async with _make_client() as client:
            result = await client.import_design_url(request)
            script_logger.info(f"Design imported: {result.get('designs', [{}])[0].get('id', '?')}")
            return {"status": "success", **result}
    except CanvaAPIError as e:
        script_logger.error(f"Canva API error in import_design: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in import_design: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def resize_design(
    design_id: str,
    width: int,
    height: int,
) -> dict:
    """
    Create a resized copy of an existing design.

    The original design is unchanged; a new design is created at the specified
    dimensions. Useful for repurposing designs across formats (e.g. Instagram
    post → LinkedIn banner).

    Args:
        design_id: The source design ID
        width: New width in pixels (40-8000)
        height: New height in pixels (40-8000)

    Returns:
        dict with new design_id, url, thumbnail_url
    """
    try:
        request = ResizeDesignRequest(design_id=design_id, width=width, height=height)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    try:
        async with _make_client() as client:
            result = await client.resize_design(request)
            script_logger.info(f"Design resized: {result.get('design_id')}")
            return {"status": "success", **result}
    except CanvaAPIError as e:
        script_logger.error(f"Canva API error in resize_design: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in resize_design: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def get_design_pages(design_id: str) -> dict:
    """
    Get page metadata for a multi-page design.

    Returns page dimensions, thumbnails, and count for each page in the design.

    Args:
        design_id: The Canva design ID

    Returns:
        dict with pages list and page count
    """
    if not design_id:
        return {"status": "error", "message": "design_id is required"}
    try:
        async with _make_client() as client:
            result = await client.get_design_pages(design_id)
            script_logger.info(f"Retrieved pages for design: {design_id}")
            return {"status": "success", **result}
    except CanvaAPIError as e:
        script_logger.error(f"Canva API error in get_design_pages: {e.message}")
        return {"status": "error", "message": e.message, "error_code": e.error_code}
    except Exception as e:
        script_logger.error(f"Unexpected error in get_design_pages: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
