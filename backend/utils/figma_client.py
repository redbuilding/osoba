"""
Async HTTP client for Figma REST API.
Handles file reading, node extraction, image export, comment management,
and design token extraction.
"""
from __future__ import annotations

import asyncio
import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("figma_client")

FIGMA_BASE_URL = os.getenv("FIGMA_BASE_URL", "https://api.figma.com/v1")
FIGMA_RATE_LIMIT_REQUESTS = int(os.getenv("FIGMA_RATE_LIMIT_REQUESTS", "1000"))
FIGMA_RATE_LIMIT_WINDOW = int(os.getenv("FIGMA_RATE_LIMIT_WINDOW", "3600"))


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    """Figma node types."""
    DOCUMENT = "DOCUMENT"
    CANVAS = "CANVAS"
    FRAME = "FRAME"
    GROUP = "GROUP"
    VECTOR = "VECTOR"
    BOOLEAN = "BOOLEAN"
    STAR = "STAR"
    LINE = "LINE"
    ELLIPSE = "ELLIPSE"
    REGULAR_POLYGON = "REGULAR_POLYGON"
    RECTANGLE = "RECTANGLE"
    TEXT = "TEXT"
    SLICE = "SLICE"
    COMPONENT = "COMPONENT"
    COMPONENT_SET = "COMPONENT_SET"
    INSTANCE = "INSTANCE"
    STICKY = "STICKY"
    SHAPE_WITH_TEXT = "SHAPE_WITH_TEXT"
    CONNECTOR = "CONNECTOR"
    WIDGET = "WIDGET"
    EMBED = "EMBED"
    LINK_UNFURL = "LINK_UNFURL"
    MEDIA = "MEDIA"
    SECTION = "SECTION"


class PaintType(str, Enum):
    """Figma paint/fill types."""
    SOLID = "SOLID"
    GRADIENT_LINEAR = "GRADIENT_LINEAR"
    GRADIENT_RADIAL = "GRADIENT_RADIAL"
    GRADIENT_ANGULAR = "GRADIENT_ANGULAR"
    GRADIENT_DIAMOND = "GRADIENT_DIAMOND"
    IMAGE = "IMAGE"
    EMOJI = "EMOJI"


class StrokeAlign(str, Enum):
    INSIDE = "INSIDE"
    OUTSIDE = "OUTSIDE"
    CENTER = "CENTER"


class LayoutMode(str, Enum):
    NONE = "NONE"
    HORIZONTAL = "HORIZONTAL"
    VERTICAL = "VERTICAL"


class PrimaryAxisAlignItems(str, Enum):
    MIN = "MIN"
    CENTER = "CENTER"
    MAX = "MAX"
    SPACE_BETWEEN = "SPACE_BETWEEN"


class CounterAxisAlignItems(str, Enum):
    MIN = "MIN"
    CENTER = "CENTER"
    MAX = "MAX"
    BASELINE = "BASELINE"


class ExportFormat(str, Enum):
    PNG = "png"
    JPG = "jpg"
    SVG = "svg"
    PDF = "pdf"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class Color(BaseModel):
    """RGBA color value (channels 0-1)."""
    r: float = Field(..., ge=0, le=1)
    g: float = Field(..., ge=0, le=1)
    b: float = Field(..., ge=0, le=1)
    a: float = Field(..., ge=0, le=1)


class Paint(BaseModel):
    """Fill/stroke paint definition."""
    type: PaintType
    color: Optional[Color] = None
    opacity: Optional[float] = Field(None, ge=0, le=1)
    visible: Optional[bool] = None
    blendMode: Optional[str] = None


class Vector(BaseModel):
    x: float
    y: float


class Rectangle(BaseModel):
    x: float
    y: float
    width: float
    height: float


class ExportSetting(BaseModel):
    suffix: str
    format: str = Field(..., pattern="^(PNG|JPG|SVG|PDF)$")
    constraint: Dict[str, Any]


class TypeStyle(BaseModel):
    fontFamily: Optional[str] = None
    fontPostScriptName: Optional[str] = None
    paragraphSpacing: Optional[float] = None
    paragraphIndent: Optional[float] = None
    listSpacing: Optional[float] = None
    hangingPunctuation: Optional[bool] = None
    hangingList: Optional[bool] = None
    fontSize: Optional[float] = None
    textAlignHorizontal: Optional[str] = None
    textAlignVertical: Optional[str] = None
    letterSpacing: Optional[float] = None
    fills: Optional[List[Paint]] = None
    hyperlink: Optional[Dict[str, Any]] = None


class ComponentProperty(BaseModel):
    type: str
    defaultValue: Union[str, bool, float, None] = None
    variantOptions: Optional[List[str]] = None


class Node(BaseModel):
    """Base Figma node — supports recursive children."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    type: NodeType
    visible: Optional[bool] = True

    # Transform and geometry
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    rotation: Optional[float] = None

    # Styling
    fills: Optional[List[Paint]] = None
    strokes: Optional[List[Paint]] = None
    strokeWeight: Optional[float] = None
    strokeAlign: Optional[StrokeAlign] = None
    cornerRadius: Optional[float] = None

    # Layout
    layoutMode: Optional[LayoutMode] = None
    primaryAxisAlignItems: Optional[PrimaryAxisAlignItems] = None
    counterAxisAlignItems: Optional[CounterAxisAlignItems] = None
    paddingLeft: Optional[float] = None
    paddingRight: Optional[float] = None
    paddingTop: Optional[float] = None
    paddingBottom: Optional[float] = None
    itemSpacing: Optional[float] = None

    # Content
    characters: Optional[str] = None
    style: Optional[TypeStyle] = None

    # Component references
    componentId: Optional[str] = None
    componentProperties: Optional[Dict[str, ComponentProperty]] = None

    # Recursive children
    children: Optional[List["Node"]] = None

    # Metadata
    exportSettings: Optional[List[ExportSetting]] = None
    blendMode: Optional[str] = None
    opacity: Optional[float] = Field(None, ge=0, le=1)


# Resolve the forward reference for Node.children
Node.model_rebuild()


class ComponentMetadata(BaseModel):
    key: str
    name: str
    description: Optional[str] = None
    componentSetId: Optional[str] = None


class Style(BaseModel):
    key: str
    name: str
    styleType: str
    description: Optional[str] = None


class FileResponse(BaseModel):
    """Figma /files/{file_key} response."""
    name: str
    lastModified: str
    thumbnailUrl: Optional[str] = None
    version: str
    document: Node
    components: Optional[Dict[str, ComponentMetadata]] = None
    componentSets: Optional[Dict[str, ComponentMetadata]] = None
    schemaVersion: Optional[int] = None
    styles: Optional[Dict[str, Style]] = None


class FileNodesResponse(BaseModel):
    """Figma /files/{file_key}/nodes response."""
    name: str
    lastModified: str
    thumbnailUrl: Optional[str] = None
    version: str
    nodes: Dict[str, Optional[Node]]
    components: Optional[Dict[str, ComponentMetadata]] = None
    componentSets: Optional[Dict[str, ComponentMetadata]] = None
    schemaVersion: Optional[int] = None
    styles: Optional[Dict[str, Style]] = None


class Comment(BaseModel):
    """Figma comment."""
    id: str
    file_key: Optional[str] = None
    parent_id: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None
    message: str
    client_meta: Optional[Dict[str, Any]] = None
    order_id: Optional[int] = None


class CommentsResponse(BaseModel):
    comments: List[Comment]


class ImageResponse(BaseModel):
    err: Optional[str] = None
    images: Optional[Dict[str, Optional[str]]] = None


class DesignToken(BaseModel):
    name: str
    type: str  # color, typography, spacing, effect, etc.
    value: Union[str, float, Dict[str, Any], Color]
    description: Optional[str] = None
    reference: Optional[str] = None


class DesignSystem(BaseModel):
    file_key: str
    name: str
    colors: List[DesignToken] = Field(default_factory=list)
    typography: List[DesignToken] = Field(default_factory=list)
    spacing: List[DesignToken] = Field(default_factory=list)
    effects: List[DesignToken] = Field(default_factory=list)
    components: List[ComponentMetadata] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class FigmaAPIError(Exception):
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

class FigmaClient:
    """Async client for the Figma REST API with sliding-window rate limiting."""

    def __init__(self, token: str):
        self.token = token
        self.client = httpx.AsyncClient(
            base_url=FIGMA_BASE_URL,
            headers={
                "X-Figma-Token": token,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self._request_times: List[float] = []
        self._lock = asyncio.Lock()

    async def _rate_limit(self) -> None:
        """Sliding-window rate limiter (1000 req/hour by default)."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            self._request_times = [
                t for t in self._request_times
                if now - t < FIGMA_RATE_LIMIT_WINDOW
            ]
            if len(self._request_times) >= FIGMA_RATE_LIMIT_REQUESTS:
                sleep_time = FIGMA_RATE_LIMIT_WINDOW - (now - self._request_times[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            self._request_times.append(now)

    async def _handle_error(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                error_data = e.response.json()
            except Exception:
                error_data = {}
            error_code = error_data.get("err", "FIGMA_API_ERROR")
            message = error_data.get("message", str(e))
            logger.error(f"Figma API HTTP error {status_code}: {message}")
            raise FigmaAPIError(
                message=message,
                status_code=status_code,
                error_code=error_code,
                response_data=error_data,
            )

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self) -> "FigmaClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def get_file(
        self,
        file_key: str,
        depth: Optional[int] = None,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get Figma file structure and metadata."""
        await self._rate_limit()
        params: Dict[str, Any] = {}
        if depth is not None:
            params["depth"] = depth
        if version:
            params["version"] = version
        response = await self.client.get(f"/files/{file_key}", params=params)
        await self._handle_error(response)
        return FileResponse.model_validate(response.json()).model_dump()

    async def get_file_nodes(
        self,
        file_key: str,
        node_ids: List[str],
        depth: Optional[int] = None,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get specific nodes from a Figma file."""
        await self._rate_limit()
        params: Dict[str, Any] = {"ids": ",".join(node_ids)}
        if depth is not None:
            params["depth"] = depth
        if version:
            params["version"] = version
        response = await self.client.get(f"/files/{file_key}/nodes", params=params)
        await self._handle_error(response)
        return FileNodesResponse.model_validate(response.json()).model_dump()

    async def get_images(
        self,
        file_key: str,
        node_ids: List[str],
        format: str = "png",
        scale: float = 1.0,
        svg_include_id: bool = False,
        svg_simplify_stroke: bool = True,
    ) -> Dict[str, Any]:
        """Export nodes as images, returns dict of node_id -> URL."""
        await self._rate_limit()
        params: Dict[str, Any] = {
            "ids": ",".join(node_ids),
            "format": format,
            "scale": scale,
        }
        if format == "svg":
            params["svg_include_id"] = str(svg_include_id).lower()
            params["svg_simplify_stroke"] = str(svg_simplify_stroke).lower()
        response = await self.client.get(f"/images/{file_key}", params=params)
        await self._handle_error(response)
        return response.json()

    async def get_comments(self, file_key: str) -> Dict[str, Any]:
        """Get all comments on a Figma file."""
        await self._rate_limit()
        response = await self.client.get(f"/files/{file_key}/comments")
        await self._handle_error(response)
        data = response.json()
        for comment in data.get("comments", []):
            comment["file_key"] = file_key
        return CommentsResponse.model_validate(data).model_dump()

    async def post_comment(
        self,
        file_key: str,
        message: str,
        node_id: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post a comment to a Figma file."""
        await self._rate_limit()
        payload: Dict[str, Any] = {"message": message}
        if node_id:
            payload["client_meta"] = {"node_id": node_id}
        if parent_id:
            payload["parent_id"] = parent_id
        response = await self.client.post(f"/files/{file_key}/comments", json=payload)
        await self._handle_error(response)
        data = response.json()
        data["file_key"] = file_key
        return Comment.model_validate(data).model_dump()

    def _extract_design_tokens(self, node: Node, tokens: List[DesignToken]) -> None:
        """Recursively extract design tokens from the node tree."""
        if node.fills:
            for i, fill in enumerate(node.fills):
                if fill.type == PaintType.SOLID and fill.color:
                    tokens.append(DesignToken(
                        name=f"{node.name}-fill-{i}",
                        type="color",
                        value=fill.color,
                        reference=node.id,
                    ))
        if node.style and node.type == NodeType.TEXT:
            if node.style.fontSize:
                tokens.append(DesignToken(
                    name=f"{node.name}-font-size",
                    type="typography",
                    value=node.style.fontSize,
                    reference=node.id,
                ))
            if node.style.fontFamily:
                tokens.append(DesignToken(
                    name=f"{node.name}-font-family",
                    type="typography",
                    value=node.style.fontFamily,
                    reference=node.id,
                ))
        if node.layoutMode and node.layoutMode != LayoutMode.NONE:
            if node.itemSpacing:
                tokens.append(DesignToken(
                    name=f"{node.name}-spacing",
                    type="spacing",
                    value=node.itemSpacing,
                    reference=node.id,
                ))
        if node.children:
            for child in node.children:
                self._extract_design_tokens(child, tokens)

    async def get_design_system(self, file_key: str) -> Dict[str, Any]:
        """Extract design tokens and component catalog from a Figma file."""
        await self._rate_limit()
        response = await self.client.get(f"/files/{file_key}", params={"depth": 2})
        await self._handle_error(response)
        file_data = FileResponse.model_validate(response.json())

        tokens: List[DesignToken] = []
        self._extract_design_tokens(file_data.document, tokens)

        if file_data.styles:
            for key, style in file_data.styles.items():
                tokens.append(DesignToken(
                    name=style.name,
                    type=style.styleType.lower(),
                    value=key,
                    description=style.description,
                    reference=key,
                ))

        colors = [t for t in tokens if t.type == "color"]
        typography = [t for t in tokens if t.type == "typography"]
        spacing = [t for t in tokens if t.type == "spacing"]
        effects = [t for t in tokens if t.type == "effect"]
        components = list(file_data.components.values()) if file_data.components else []

        return DesignSystem(
            file_key=file_key,
            name=file_data.name,
            colors=colors,
            typography=typography,
            spacing=spacing,
            effects=effects,
            components=components,
        ).model_dump()
