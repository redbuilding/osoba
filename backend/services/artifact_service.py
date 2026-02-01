from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from core.config import BASE_DIR, ARTIFACTS_ROOT, get_logger

logger = get_logger("artifact_service")


def _repo_root() -> Path:
    # backend/.. is repo root
    return Path(BASE_DIR).parent.resolve()


def _artifacts_root_abs() -> Path:
    root = Path(ARTIFACTS_ROOT)
    if not root.is_absolute():
        root = _repo_root() / root
    return root.resolve()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _slugify(text: str, max_len: int = 80) -> str:
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in (text or "").strip())
    safe = "-".join(filter(None, safe.split("-")))
    if not safe:
        safe = "untitled"
    return safe[:max_len]


def sanitize_relpath(rel_path: str) -> Path:
    # prevent traversal and strip drive letters
    rel = rel_path.replace("\\", "/").lstrip("/")
    parts = [p for p in rel.split("/") if p not in ("..", "")]
    return Path("/").joinpath(*parts).relative_to("/")


def versioned_path(root: Path, desired: Path) -> Path:
    candidate = root / desired
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    parent = candidate.parent
    i = 2
    while True:
        alt = parent / f"{stem}-v{i}{suffix}"
        if not alt.exists():
            return alt
        i += 1


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


@dataclass
class Artifact:
    id: str
    source_type: str  # message|task_run
    source_id: Optional[str]
    title: str
    format: str  # md|html|docx|pdf
    path: str
    size: int
    checksum: str
    created_at: datetime


class ArtifactService:
    def __init__(self) -> None:
        self.root = _artifacts_root_abs()
        _ensure_dir(self.root)

    def write_text(self, rel_path: str, text: str) -> Tuple[Path, int, str]:
        safe_rel = sanitize_relpath(rel_path)
        abs_target = versioned_path(self.root, safe_rel)
        _ensure_dir(abs_target.parent)
        data = (text or "").encode("utf-8")
        abs_target.write_bytes(data)
        return abs_target, len(data), sha256_bytes(data)

    def write_bytes(self, rel_path: str, data: bytes) -> Tuple[Path, int, str]:
        safe_rel = sanitize_relpath(rel_path)
        abs_target = versioned_path(self.root, safe_rel)
        _ensure_dir(abs_target.parent)
        abs_target.write_bytes(data)
        return abs_target, len(data), sha256_bytes(data)

    def default_message_path(self, title: str, ext: str = ".md") -> str:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        slug = _slugify(title)
        return f"messages/{date}/{slug}{ext}"

    def default_task_path(self, task_slug: str, run_id: str, title: str, ext: str = ".md") -> str:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        slug = _slugify(title)
        tslug = _slugify(task_slug)
        return f"tasks/{date}/{tslug}/{run_id}-{slug}{ext}"


artifact_service = ArtifactService()

