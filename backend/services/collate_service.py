from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any

from core.config import get_logger
from db.tasks_crud import get_task

logger = get_logger("collate_service")


DEFAULT_OPTIONS = {
    "include_headers": True,
    "include_system_prompt": False,
    "include_step_titles": True,
    "include_timestamps": True,
    "include_llm_responses": True,
    "include_tool_outputs": "summary",  # none|summary|full
    "include_sources": False,
}


def _md_escape(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")


def build_markdown(task_id: str, options: Dict[str, Any] | None = None) -> str:
    opts = {**DEFAULT_OPTIONS, **(options or {})}
    doc = get_task(task_id)
    if not doc:
        raise ValueError("Task not found")

    title = doc.get("title") or doc.get("goal") or "Task"
    created = doc.get("created_at")
    model_name = doc.get("model_name") or ""
    profile = doc.get("profile_id") or ""
    now = datetime.now(timezone.utc)

    lines: list[str] = []
    if opts["include_headers"]:
        lines.append(f"# {title}")
        lines.append("")
        lines.append("| Key | Value |")
        lines.append("| --- | ----- |")
        lines.append(f"| Task ID | `{task_id}` |")
        if created:
            lines.append(f"| Created | {created} |")
        lines.append(f"| Exported | {now.isoformat()} |")
        if model_name:
            lines.append(f"| Model | `{_md_escape(model_name)}` |")
        if profile:
            lines.append(f"| Profile | `{_md_escape(profile)}` |")
        lines.append("")

    # Steps
    plan = (doc.get("plan") or {})
    steps = plan.get("steps") or []
    for i, s in enumerate(steps):
        stitle = s.get("title") or s.get("tool") or f"Step {i+1}"
        if opts["include_step_titles"]:
            lines.append(f"## Step {i+1} — {stitle}")
        status = s.get("status") or "PENDING"
        lines.append(f"- Status: `{status}`")
        tool = s.get("tool")
        if tool:
            lines.append(f"- Tool: `{tool}`")
        if opts["include_timestamps"]:
            if s.get("started_at"):
                lines.append(f"- Started: {s.get('started_at')}")
            if s.get("ended_at"):
                lines.append(f"- Ended: {s.get('ended_at')}")
        outputs = s.get("outputs") or {}
        text = outputs.get("text")
        raw = outputs.get("raw")
        if opts["include_llm_responses"] and text:
            lines.append("")
            lines.append(text)
            lines.append("")
        if opts["include_tool_outputs"] in ("summary", "full") and raw is not None:
            lines.append("")
            if isinstance(raw, str):
                snippet = raw if opts["include_tool_outputs"] == "full" else raw[:2000]
                lines.append("```\n" + snippet + ("\n..." if len(raw) > len(snippet) else "") + "\n```")
            else:
                import json
                js = json.dumps(raw, indent=2)
                snippet = js if opts["include_tool_outputs"] == "full" else js[:2000]
                lines.append("```json\n" + snippet + ("\n..." if len(js) > len(snippet) else "") + "\n```")
            lines.append("")
        if s.get("error"):
            lines.append("")
            lines.append(f"> Error: {s['error']}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"

