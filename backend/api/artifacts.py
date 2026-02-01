from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core.config import get_logger
from services.artifact_service import artifact_service
from services.path_renderer import render_path_template
from services.collate_service import build_markdown
from services.render_service import (
    render_markdown_to_html,
    render_html_template,
    render_docx_from_markdown,
    html_to_pdf_bytes,
    get_capabilities,
)
from db.tasks_crud import get_task

router = APIRouter()
logger = get_logger("api_artifacts")


@router.get("/api/artifacts/capabilities")
async def artifact_capabilities():
    caps = get_capabilities()
    return {"html": caps.html, "docx": caps.docx, "pdf": caps.pdf}


@router.post("/api/artifacts")
async def create_artifact(payload: dict):
    """
    Create an artifact by saving content to the artifacts root.

    Expected body fields:
    - source_type: 'message' | 'task_run'
    - content?: string (required if source_type='message')
    - task_id?: string (required if source_type='task_run')
    - format: 'md' | 'html' | 'docx' | 'pdf' (currently supports 'md')
    - path_template: string (e.g., 'artifacts/{date}/messages/{title}.md' or relative to artifacts root)
    - options?: dict (collation options for task_run)
    - title?: string (used in path rendering)
    - profile?: string (used in path rendering)
    """
    try:
      
        src_type = (payload.get("source_type") or "").lower()
        fmt = (payload.get("format") or "md").lower()
        if src_type not in ("message", "task_run"):
            raise HTTPException(status_code=400, detail="Invalid source_type")
        if fmt not in ("md", "markdown", "html", "pdf", "docx"):
            raise HTTPException(status_code=400, detail="Unsupported format")

        # Resolve content
        content = None
        ctx = {
            "title": payload.get("title") or ("Task Run" if src_type == "task_run" else "Message"),
            "profile": payload.get("profile") or "",
        }
        run_id = ""
        if src_type == "message":
            content = payload.get("content")
            if not isinstance(content, str) or not content.strip():
                raise HTTPException(status_code=400, detail="Missing content for message save")
        else:
            task_id = payload.get("task_id")
            if not task_id:
                raise HTTPException(status_code=400, detail="Missing task_id for task_run save")
            doc = get_task(task_id)
            if not doc:
                raise HTTPException(status_code=404, detail="Task not found")
            status = doc.get("status")
            if status in ("PLANNING", "PENDING", "RUNNING"):
                raise HTTPException(status_code=409, detail="Task is not complete. Try again after it finishes.")
            ctx.update({
                "task_slug": doc.get("title") or doc.get("goal") or task_id,
                "run_id": str(doc.get("_id") or task_id),
                "title": doc.get("title") or doc.get("goal") or "Task",
            })
            content = build_markdown(task_id, payload.get("options"))
            run_id = ctx["run_id"]

        # Render path
        path_template = payload.get("path_template") or (
            artifact_service.default_task_path(ctx.get("task_slug", "task"), run_id, ctx.get("title", "Task"))
            if src_type == "task_run" else artifact_service.default_message_path(ctx.get("title", "Message"))
        )
        # Allow callers to include leading 'artifacts/' but store relative to artifacts root
        if path_template.startswith("artifacts/"):
            path_template = path_template[len("artifacts/"):]
        # Force extension to match selected format
        desired_ext = {
            "md": ".md",
            "markdown": ".md",
            "html": ".html",
            "pdf": ".pdf",
            "docx": ".docx",
        }[fmt]
        rendered_rel = render_path_template(path_template, ctx)
        from pathlib import Path as _P
        p = _P(rendered_rel)
        if p.suffix.lower() != desired_ext:
            p = p.with_suffix(desired_ext)

        # Render per format
        if fmt in ("md", "markdown"):
            abspath, size, checksum = artifact_service.write_text(str(p), content)
        elif fmt == "html":
            # Collated markdown (for task) or message markdown -> HTML via Jinja
            html_body = render_markdown_to_html(content)
            html_full = render_html_template(
                "html/branded_report.html.j2",
                {
                    "title": ctx.get("title") or ("Task Run" if src_type == "task_run" else "Message"),
                    "task_id": ctx.get("run_id") if src_type == "task_run" else None,
                    "model_name": payload.get("model_name") or "",
                    "profile": ctx.get("profile") or "",
                    "exported_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                    "content_html": html_body,
                },
            )
            abspath, size, checksum = artifact_service.write_bytes(str(p), html_full.encode("utf-8"))
        elif fmt == "docx":
            docx_bytes = render_docx_from_markdown(content)
            abspath, size, checksum = artifact_service.write_bytes(str(p), docx_bytes)
        elif fmt == "pdf":
            html_body = render_markdown_to_html(content)
            html_full = render_html_template(
                "html/branded_report.html.j2",
                {
                    "title": ctx.get("title") or ("Task Run" if src_type == "task_run" else "Message"),
                    "task_id": ctx.get("run_id") if src_type == "task_run" else None,
                    "model_name": payload.get("model_name") or "",
                    "profile": ctx.get("profile") or "",
                    "exported_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                    "content_html": html_body,
                },
            )
            if not get_capabilities().pdf:
                raise HTTPException(status_code=503, detail="PDF renderer unavailable")
            pdf_bytes = await html_to_pdf_bytes(html_full)
            abspath, size, checksum = artifact_service.write_bytes(str(p), pdf_bytes)

        logger.info(f"Artifact saved: {abspath}")
        return {
            "path": str(abspath),
            "relative_path": str(p),
            "size": size,
            "checksum": checksum,
            "format": fmt if fmt != "markdown" else "md",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating artifact: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating artifact")
