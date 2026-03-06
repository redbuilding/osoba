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
        created_at = datetime.now(timezone.utc).isoformat()
        updated_at = datetime.now(timezone.utc).isoformat()
        if "created_at" in data:
            try:
                created_at = datetime.fromisoformat(
                    data["created_at"].replace("Z", "+00:00")
                ).isoformat()
            except (ValueError, AttributeError):
                pass
        if "updated_at" in data:
            try:
                updated_at = datetime.fromisoformat(
                    data["updated_at"].replace("Z", "+00:00")
                ).isoformat()
            except (ValueError, AttributeError):
                pass
        return {
            "id": data["id"],
            "title": data.get("title", "Untitled"),
            "created_at": created_at,
            "updated_at": updated_at,
            "width": data.get("width", 0),
            "height": data.get("height", 0),
            "url": data.get("urls", {}).get("edit", data.get("url", "")),
            "thumbnail_url": data.get("thumbnail", {}).get("url"),
            "type": data.get("type"),
            "owner_id": data.get("owner", {}).get("id"),
            "team_id": data.get("team", {}).get("id"),
        }

    async def create_design(self, request: CreateDesignRequest) -> Dict[str, Any]:
        if request.brand_template_id:
            return await self._create_design_via_autofill(request)
        return await self._create_design_regular(request)

    async def _create_design_regular(self, request: CreateDesignRequest) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"title": request.title}
        if request.preset and request.preset.value != "custom":
            payload["preset"] = request.preset.value
        elif request.size:
            payload["width"] = request.size.width
            payload["height"] = request.size.height
            payload["unit"] = request.size.unit.value
        if request.template_id:
            payload["template_id"] = request.template_id
        response = await self.client.post("/designs", json=payload)
        await self._handle_error(response)
        return self._parse_design(response.json())

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
        return self._parse_design(response.json())

    async def export_design(self, request: ExportDesignRequest) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"format": request.format.value}
        if request.width:
            payload["width"] = request.width
        if request.height:
            payload["height"] = request.height
        if request.quality:
            payload["quality"] = request.quality
        if request.pages:
            payload["pages"] = request.pages
        response = await self.client.post(
            f"/designs/{request.design_id}/exports", json=payload
        )
        await self._handle_error(response)
        data = response.json()
        job_id = data["id"]
        status = ExportStatus(data.get("status", "pending"))
        if status not in (ExportStatus.COMPLETED, ExportStatus.FAILED):
            return await self._poll_export_job(job_id, request.design_id, request.format.value)
        return self._build_export_result(data, request.design_id, request.format.value)

    async def _poll_export_job(
        self, job_id: str, design_id: str, fmt: str
    ) -> Dict[str, Any]:
        max_attempts = DEFAULT_EXPORT_TIMEOUT // EXPORT_POLL_INTERVAL
        for attempt in range(max_attempts):
            response = await self.client.get(f"/exports/{job_id}")
            await self._handle_error(response)
            data = response.json()
            status = ExportStatus(data.get("status", "pending"))
            if status in (ExportStatus.COMPLETED, ExportStatus.FAILED):
                return self._build_export_result(data, design_id, fmt)
            logger.debug(f"Export job {job_id} status={status.value} (attempt {attempt + 1})")
            await asyncio.sleep(EXPORT_POLL_INTERVAL)
        raise CanvaAPIError(
            f"Export job {job_id} did not complete within {DEFAULT_EXPORT_TIMEOUT}s",
            error_code="EXPORT_TIMEOUT",
        )

    def _build_export_result(
        self, data: Dict[str, Any], design_id: str, fmt: str
    ) -> Dict[str, Any]:
        return {
            "job_id": data.get("id", ""),
            "status": data.get("status", "unknown"),
            "design_id": design_id,
            "format": fmt,
            "download_url": data.get("url"),
            "file_size_bytes": data.get("file_size_bytes"),
            "error_code": data.get("error_code"),
            "error_message": data.get("error_message"),
        }

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
