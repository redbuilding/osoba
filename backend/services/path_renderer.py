from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from .artifact_service import _slugify


def render_path_template(tmpl: str, ctx: Dict[str, str]) -> str:
    now = datetime.now(timezone.utc)
    base = {
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.strftime("%Y%m%d-%H%M%S"),
        **{k: v for k, v in ctx.items() if isinstance(v, str)},
    }
    # slugify main tokens to keep paths safe
    for key in ("task_slug", "run_id", "title", "profile"):
        if key in base:
            base[key] = _slugify(base[key])
    try:
        return tmpl.format(**base)
    except Exception:
        # On template error, fall back to safe default
        return f"messages/{base['date']}/{base.get('title','untitled')}.md"

