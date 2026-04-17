"""
Async HTTP client for Canva Connect API.
Handles design creation, listing, retrieval, and export operations.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger("canva_client")

CANVA_BASE_URL = os.getenv("CANVA_BASE_URL", "https://api.canva.com/rest/v1")
EXPORT_POLL_INTERVAL = int(os.getenv("CANVA_EXPORT_POLL_INTERVAL", "2"))
DEFAULT_EXPORT_TIMEOUT = int(os.getenv("CANVA_EXPORT_TIMEOUT", "300"))


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class DesignPreset(str, Enum):
    INSTAGRAM_POST = "instagram_post"
    INSTAGRAM_STORY = "instagram_story"
    FACEBOOK_POST = "facebook_post"
    FACEBOOK_COVER = "facebook_cover"
    TWITTER_POST = "twitter_post"
    LINKEDIN_BANNER = "linkedin_banner"
    YOUTUBE_THUMBNAIL = "youtube_thumbnail"
    PRESENTATION = "presentation"
    A4 = "a4"
    A3 = "a3"
    US_LETTER = "us_letter"
    CUSTOM = "custom"


class DesignUnit(str, Enum):
    PIXELS = "px"
    MILLIMETERS = "mm"
    INCHES = "in"
    POINTS = "pt"


class ExportFormat(str, Enum):
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    PDF = "pdf"
    SVG = "svg"
    MP4 = "mp4"
    GIF = "gif"


class ExportStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DesignSize(BaseModel):
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    unit: DesignUnit = DesignUnit.PIXELS


class CreateDesignRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    preset: Optional[DesignPreset] = None
    size: Optional[DesignSize] = None
    template_id: Optional[str] = None
    brand_template_id: Optional[str] = None
    autofill_data: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_size_or_preset(self):
        if self.preset is None and self.size is None:
            raise ValueError("Either preset or size must be provided")
        if self.preset == DesignPreset.CUSTOM and self.size is None:
            raise ValueError("size must be provided when preset is CUSTOM")
        return self


class ExportDesignRequest(BaseModel):
    design_id: str = Field(..., min_length=1)
    format: ExportFormat = ExportFormat.PNG
    width: Optional[int] = Field(None, gt=0)
    height: Optional[int] = Field(None, gt=0)
    quality: Optional[int] = Field(None, ge=1, le=100)
    pages: Optional[List[int]] = None

    @field_validator("quality")
    @classmethod
    def validate_quality_for_jpg(cls, v: Optional[int], info: Any) -> Optional[int]:
        if v is not None:
            fmt = info.data.get("format")
            if fmt not in [ExportFormat.JPG, ExportFormat.JPEG]:
                raise ValueError("quality is only valid for JPG/JPEG format")
        return v


class AssetUploadRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=8, max_length=2048)


class ImportDesignRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1, max_length=2048)
    mime_type: Optional[str] = None


class ResizeDesignRequest(BaseModel):
    design_id: str = Field(..., min_length=1)
    width: int = Field(..., ge=40, le=8000)
    height: int = Field(..., ge=40, le=8000)


class CanvaAPIError(Exception):
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
# Client
# ---------------------------------------------------------------------------

class CanvaClient:
    """Async client for the Canva Connect API."""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.client = httpx.AsyncClient(
            base_url=CANVA_BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Osoba-Canva-MCP/1.0",
            },
            timeout=30.0,
            follow_redirects=True,
        )

    async def _handle_error(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                error_data = e.response.json()
            except Exception:
                error_data = {}
            error_code = error_data.get("error", "CANVA_API_ERROR")
            message = error_data.get("message", str(e))
            logger.error(f"Canva API HTTP error {status_code}: {message}")
            raise CanvaAPIError(
                message=message,
                status_code=status_code,
                error_code=error_code,
                response_data=error_data,
            )

    def _parse_design(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Handle created_at/updated_at as either ISO string or Unix timestamp
        def _parse_ts(val: Any) -> str:
            if val is None:
                return datetime.now(timezone.utc).isoformat()
            if isinstance(val, (int, float)):
                return datetime.fromtimestamp(val, tz=timezone.utc).isoformat()
            try:
                return datetime.fromisoformat(str(val).replace("Z", "+00:00")).isoformat()
            except (ValueError, AttributeError):
                return datetime.now(timezone.utc).isoformat()

        urls = data.get("urls", {})
        return {
            "id": data.get("id", ""),
            "title": data.get("title", "Untitled"),
            "created_at": _parse_ts(data.get("created_at")),
            "updated_at": _parse_ts(data.get("updated_at")),
            "width": data.get("width", 0),
            "height": data.get("height", 0),
            "url": urls.get("edit_url", urls.get("edit", data.get("url", ""))),
            "thumbnail_url": data.get("thumbnail", {}).get("url"),
            "type": data.get("type"),
            "owner_id": data.get("owner", {}).get("id"),
            "team_id": data.get("team", {}).get("id"),
        }

    async def create_design(self, request: CreateDesignRequest) -> Dict[str, Any]:
        if request.brand_template_id:
            return await self._create_design_via_autofill(request)
        return await self._create_design_regular(request)

    # Preset → dimensions mapping for presets that aren't native Canva design types
    _PRESET_DIMENSIONS = {
        "instagram_post": (1080, 1080),
        "instagram_story": (1080, 1920),
        "facebook_post": (1200, 630),
        "facebook_cover": (820, 312),
        "twitter_post": (1200, 675),
        "linkedin_banner": (1584, 396),
        "youtube_thumbnail": (1280, 720),
        "a4": (595, 842),
        "a3": (842, 1191),
        "us_letter": (612, 792),
    }
    # Presets that map directly to Canva's native design types
    _NATIVE_PRESETS = {"presentation", "doc", "email", "whiteboard"}

    async def _create_design_regular(self, request: CreateDesignRequest) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"type": "type_and_asset"}
        if request.title:
            payload["title"] = request.title
        if request.preset and request.preset.value != "custom":
            preset_val = request.preset.value
            if preset_val in self._NATIVE_PRESETS:
                payload["design_type"] = {"type": "preset", "name": preset_val}
            elif preset_val in self._PRESET_DIMENSIONS:
                w, h = self._PRESET_DIMENSIONS[preset_val]
                payload["design_type"] = {"type": "custom", "width": w, "height": h}
            else:
                payload["design_type"] = {"type": "preset", "name": preset_val}
        elif request.size:
            payload["design_type"] = {
                "type": "custom",
                "width": request.size.width,
                "height": request.size.height,
            }
        if request.template_id:
            payload["asset_id"] = request.template_id
        response = await self.client.post("/designs", json=payload)
        await self._handle_error(response)
        data = response.json()
        design = data.get("design", data)
        return self._parse_design(design)

    async def _create_design_via_autofill(self, request: CreateDesignRequest) -> Dict[str, Any]:
        payload = {
            "brand_template_id": request.brand_template_id,
            "data": request.autofill_data or {},
        }
        response = await self.client.post("/v1/autofills", json=payload)
        await self._handle_error(response)
        job_id = response.json()["id"]
        logger.info(f"Autofill job submitted: {job_id}")
        design_id = await self._poll_autofill_job(job_id)
        return await self.get_design(design_id)

    async def _poll_autofill_job(self, job_id: str) -> str:
        max_attempts = DEFAULT_EXPORT_TIMEOUT // EXPORT_POLL_INTERVAL
        for attempt in range(max_attempts):
            response = await self.client.get(f"/v1/autofills/{job_id}")
            await self._handle_error(response)
            data = response.json()
            status = data.get("status", "pending")
            if status == "completed":
                design_id = data.get("design_id")
                if not design_id:
                    raise CanvaAPIError("Autofill completed but no design_id returned")
                return design_id
            elif status == "failed":
                raise CanvaAPIError(
                    f"Autofill failed: {data.get('error_message', 'unknown error')}",
                    error_code="AUTOFILL_FAILED",
                )
            logger.debug(f"Autofill job {job_id} pending (attempt {attempt + 1})")
            await asyncio.sleep(EXPORT_POLL_INTERVAL)
        raise CanvaAPIError(
            f"Autofill job {job_id} timed out",
            error_code="AUTOFILL_TIMEOUT",
        )

    async def list_designs(
        self,
        page_token: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": min(limit, 100)}
        if page_token:
            params["continuation"] = page_token
        response = await self.client.get("/designs", params=params)
        await self._handle_error(response)
        data = response.json()
        designs = [self._parse_design(item) for item in data.get("items", [])]
        return {
            "items": designs,
            "next_page_token": data.get("continuation"),
            "total_count": data.get("total_count"),
        }

    async def get_design(self, design_id: str) -> Dict[str, Any]:
        response = await self.client.get(f"/designs/{design_id}")
        await self._handle_error(response)
        data = response.json()
        return self._parse_design(data.get("design", data))

    async def export_design(self, request: ExportDesignRequest) -> Dict[str, Any]:
        fmt_obj: Dict[str, Any] = {"type": request.format.value}
        if request.quality:
            fmt_obj["export_quality"] = "pro"
        if request.pages:
            fmt_obj["pages"] = request.pages
        payload: Dict[str, Any] = {
            "design_id": request.design_id,
            "format": fmt_obj,
        }
        response = await self.client.post("/exports", json=payload)
        await self._handle_error(response)
        data = response.json()
        job = data.get("job", data)
        job_id = job["id"]
        status = job.get("status", "in_progress")
        if status in ("success", "failed"):
            return self._build_export_result(job, request.design_id, request.format.value)
        return await self._poll_export_job(job_id, request.design_id, request.format.value)

    async def _poll_export_job(
        self, job_id: str, design_id: str, fmt: str
    ) -> Dict[str, Any]:
        max_attempts = DEFAULT_EXPORT_TIMEOUT // EXPORT_POLL_INTERVAL
        for attempt in range(max_attempts):
            response = await self.client.get(f"/exports/{job_id}")
            await self._handle_error(response)
            data = response.json()
            job = data.get("job", data)
            status = job.get("status", "in_progress")
            if status in ("success", "failed"):
                return self._build_export_result(job, design_id, fmt)
            logger.debug(f"Export job {job_id} status={status} (attempt {attempt + 1})")
            await asyncio.sleep(EXPORT_POLL_INTERVAL)
        raise CanvaAPIError(
            f"Export job {job_id} did not complete within {DEFAULT_EXPORT_TIMEOUT}s",
            error_code="EXPORT_TIMEOUT",
        )

    def _build_export_result(
        self, data: Dict[str, Any], design_id: str, fmt: str
    ) -> Dict[str, Any]:
        urls = data.get("urls", [])
        error = data.get("error", {})
        return {
            "job_id": data.get("id", ""),
            "status": data.get("status", "unknown"),
            "design_id": design_id,
            "format": fmt,
            "download_url": urls[0] if urls else None,
            "download_urls": urls,
            "error_code": error.get("code"),
            "error_message": error.get("message"),
        }

    # ------------------------------------------------------------------
    # Asset uploads
    # ------------------------------------------------------------------

    async def upload_asset_url(self, request: AssetUploadRequest) -> Dict[str, Any]:
        payload = {"name": request.name, "url": request.url}
        response = await self.client.post("/url-asset-uploads", json=payload)
        await self._handle_error(response)
        data = response.json()
        job = data.get("job", data)
        if job.get("status") == "success":
            return self._build_asset_result(job)
        return await self._poll_asset_job(job["id"])

    async def _poll_asset_job(self, job_id: str) -> Dict[str, Any]:
        max_attempts = DEFAULT_EXPORT_TIMEOUT // EXPORT_POLL_INTERVAL
        for attempt in range(max_attempts):
            response = await self.client.get(f"/url-asset-uploads/{job_id}")
            await self._handle_error(response)
            job = response.json().get("job", response.json())
            if job.get("status") == "success":
                return self._build_asset_result(job)
            if job.get("status") == "failed":
                err = job.get("error", {})
                raise CanvaAPIError(
                    err.get("message", "Asset upload failed"),
                    error_code=err.get("code", "ASSET_UPLOAD_FAILED"),
                )
            await asyncio.sleep(EXPORT_POLL_INTERVAL)
        raise CanvaAPIError(f"Asset upload job {job_id} timed out", error_code="ASSET_UPLOAD_TIMEOUT")

    def _build_asset_result(self, job: Dict[str, Any]) -> Dict[str, Any]:
        asset = job.get("asset", {})
        return {
            "job_id": job.get("id", ""),
            "status": job.get("status", "unknown"),
            "asset_id": asset.get("id"),
            "name": asset.get("name"),
            "type": asset.get("type"),
            "thumbnail_url": asset.get("thumbnail", {}).get("url"),
        }

    # ------------------------------------------------------------------
    # Autofill (first-class)
    # ------------------------------------------------------------------

    async def create_autofill(
        self, brand_template_id: str, data: Dict[str, Any], title: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"brand_template_id": brand_template_id, "data": data}
        if title:
            payload["title"] = title
        response = await self.client.post("/autofills", json=payload)
        await self._handle_error(response)
        job = response.json().get("job", response.json())
        if job.get("status") == "success":
            return self._parse_autofill_result(job)
        return await self._poll_autofill_job_v2(job["id"])

    async def _poll_autofill_job_v2(self, job_id: str) -> Dict[str, Any]:
        max_attempts = DEFAULT_EXPORT_TIMEOUT // EXPORT_POLL_INTERVAL
        for attempt in range(max_attempts):
            response = await self.client.get(f"/autofills/{job_id}")
            await self._handle_error(response)
            job = response.json().get("job", response.json())
            if job.get("status") == "success":
                return self._parse_autofill_result(job)
            if job.get("status") == "failed":
                err = job.get("error", {})
                raise CanvaAPIError(
                    err.get("message", "Autofill failed"),
                    error_code=err.get("code", "AUTOFILL_FAILED"),
                )
            await asyncio.sleep(EXPORT_POLL_INTERVAL)
        raise CanvaAPIError(f"Autofill job {job_id} timed out", error_code="AUTOFILL_TIMEOUT")

    def _parse_autofill_result(self, job: Dict[str, Any]) -> Dict[str, Any]:
        result = job.get("result", {})
        design = result.get("design", {})
        urls = design.get("urls", {})
        return {
            "job_id": job.get("id", ""),
            "status": job.get("status", "unknown"),
            "design_id": design.get("id"),
            "title": design.get("title"),
            "url": urls.get("edit_url", design.get("url", "")),
            "view_url": urls.get("view_url"),
            "thumbnail_url": design.get("thumbnail", {}).get("url"),
        }

    # ------------------------------------------------------------------
    # Brand template dataset
    # ------------------------------------------------------------------

    async def get_brand_template_dataset(self, brand_template_id: str) -> Dict[str, Any]:
        response = await self.client.get(f"/brand-templates/{brand_template_id}/dataset")
        await self._handle_error(response)
        return response.json()

    # ------------------------------------------------------------------
    # Design import (URL)
    # ------------------------------------------------------------------

    async def import_design_url(self, request: ImportDesignRequest) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"title": request.title, "url": request.url}
        if request.mime_type:
            payload["mime_type"] = request.mime_type
        response = await self.client.post("/url-imports", json=payload)
        await self._handle_error(response)
        job = response.json().get("job", response.json())
        if job.get("status") == "success":
            return self._parse_import_result(job)
        return await self._poll_import_job(job["id"])

    async def _poll_import_job(self, job_id: str) -> Dict[str, Any]:
        max_attempts = DEFAULT_EXPORT_TIMEOUT // EXPORT_POLL_INTERVAL
        for attempt in range(max_attempts):
            response = await self.client.get(f"/url-imports/{job_id}")
            await self._handle_error(response)
            job = response.json().get("job", response.json())
            if job.get("status") == "success":
                return self._parse_import_result(job)
            if job.get("status") == "failed":
                err = job.get("error", {})
                raise CanvaAPIError(
                    err.get("message", "Design import failed"),
                    error_code=err.get("code", "IMPORT_FAILED"),
                )
            await asyncio.sleep(EXPORT_POLL_INTERVAL)
        raise CanvaAPIError(f"Import job {job_id} timed out", error_code="IMPORT_TIMEOUT")

    def _parse_import_result(self, job: Dict[str, Any]) -> Dict[str, Any]:
        result = job.get("result", {})
        designs = result.get("designs", [])
        parsed = []
        for d in designs:
            urls = d.get("urls", {})
            parsed.append({
                "id": d.get("id"),
                "title": d.get("title"),
                "url": urls.get("edit_url", d.get("url", "")),
                "view_url": urls.get("view_url"),
                "thumbnail_url": d.get("thumbnail", {}).get("url"),
                "page_count": d.get("page_count"),
            })
        return {
            "job_id": job.get("id", ""),
            "status": job.get("status", "unknown"),
            "designs": parsed,
        }

    # ------------------------------------------------------------------
    # Resize
    # ------------------------------------------------------------------

    async def resize_design(self, request: ResizeDesignRequest) -> Dict[str, Any]:
        payload = {
            "design_id": request.design_id,
            "design_type": {"type": "custom", "width": request.width, "height": request.height},
        }
        response = await self.client.post("/resizes", json=payload)
        await self._handle_error(response)
        job = response.json().get("job", response.json())
        if job.get("status") == "success":
            return self._parse_resize_result(job)
        return await self._poll_resize_job(job["id"])

    async def _poll_resize_job(self, job_id: str) -> Dict[str, Any]:
        max_attempts = DEFAULT_EXPORT_TIMEOUT // EXPORT_POLL_INTERVAL
        for attempt in range(max_attempts):
            response = await self.client.get(f"/resizes/{job_id}")
            await self._handle_error(response)
            job = response.json().get("job", response.json())
            if job.get("status") == "success":
                return self._parse_resize_result(job)
            if job.get("status") == "failed":
                err = job.get("error", {})
                raise CanvaAPIError(
                    err.get("message", "Resize failed"),
                    error_code=err.get("code", "RESIZE_FAILED"),
                )
            await asyncio.sleep(EXPORT_POLL_INTERVAL)
        raise CanvaAPIError(f"Resize job {job_id} timed out", error_code="RESIZE_TIMEOUT")

    def _parse_resize_result(self, job: Dict[str, Any]) -> Dict[str, Any]:
        result = job.get("result", {})
        design = result.get("design", {})
        urls = design.get("urls", {})
        return {
            "job_id": job.get("id", ""),
            "status": job.get("status", "unknown"),
            "design_id": design.get("id"),
            "title": design.get("title"),
            "url": urls.get("edit_url", design.get("url", "")),
            "view_url": urls.get("view_url"),
            "thumbnail_url": design.get("thumbnail", {}).get("url"),
        }

    # ------------------------------------------------------------------
    # Design pages
    # ------------------------------------------------------------------

    async def get_design_pages(self, design_id: str) -> Dict[str, Any]:
        response = await self.client.get(f"/designs/{design_id}/pages")
        await self._handle_error(response)
        return response.json()

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
