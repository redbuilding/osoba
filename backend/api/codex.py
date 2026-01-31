from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from services.codex_client import (
    create_workspace as codex_create_workspace,
    start_run as codex_start_run,
    get_run_status as codex_get_run_status,
    cancel_run as codex_cancel_run,
    get_manifest as codex_get_manifest,
    read_file as codex_read_file,
)
from core.config import get_logger

router = APIRouter()
logger = get_logger("api_codex")


class CreateWorkspacePayload(BaseModel):
    name_hint: str
    keep: bool = False


@router.post("/api/codex/workspaces")
async def create_workspace_endpoint(payload: CreateWorkspacePayload):
    try:
        return await codex_create_workspace(payload.name_hint, payload.keep)
    except Exception as e:
        logger.error(f"Codex create_workspace failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/codex/runs")
async def start_run_endpoint(payload: dict):
    try:
        # Be liberal in what we accept
        try:
            logger.info(f"/api/codex/runs payload keys: {list(payload.keys())}")
        except Exception:
            pass
        workspace_id = payload.get("workspace_id") or payload.get("workspaceId")
        instruction = payload.get("instruction") or payload.get("prompt") or payload.get("text") or payload.get("user_message")
        model = payload.get("model")
        try:
            timeout_seconds = int(payload.get("timeout_seconds") or payload.get("timeoutSeconds") or 900)
        except Exception:
            timeout_seconds = 900
        # If workspace_id missing, create one on the fly as a convenience
        if not workspace_id:
            try:
                name_hint = payload.get("name_hint") or payload.get("nameHint") or "task"
                ws = await codex_create_workspace(str(name_hint), keep=False)
                workspace_id = ws.get("workspace_id") or ws.get("workspaceId")
                if not workspace_id:
                    # fallback: derive from workspace_path
                    wp = ws.get("workspace_path") or ws.get("workspacePath") or ""
                    workspace_id = str(wp).rstrip("/").split("/")[-1] if wp else None
                logger.info(f"/api/codex/runs auto-created workspace: {workspace_id}")
            except Exception as e:
                logger.error(f"Failed to auto-create workspace: {e}")
        if not workspace_id or not instruction or str(instruction).strip() == "":
            keys = ",".join(list(payload.keys())[:10])
            logger.warning(f"/api/codex/runs missing fields. workspace_id={workspace_id!r} instruction_present={bool(instruction)}")
            raise HTTPException(status_code=400, detail=f"workspace_id and instruction are required; got keys: {keys}")
        result = await codex_start_run(str(workspace_id), str(instruction), model, timeout_seconds)
        try:
            run_id = result.get('run_id') or (result.get('run') or {}).get('run_id')
            if run_id:
                logger.info(f"/api/codex/runs started run_id={run_id} ws={workspace_id}")
        except Exception:
            pass
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Codex start_run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/codex/runs/{run_id}")
async def get_run_status_endpoint(run_id: str):
    try:
        return await codex_get_run_status(run_id)
    except Exception as e:
        logger.error(f"Codex get_run_status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/codex/runs/{run_id}/cancel")
async def cancel_run_endpoint(run_id: str):
    try:
        return await codex_cancel_run(run_id)
    except Exception as e:
        logger.error(f"Codex cancel_run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/codex/workspaces/{workspace_id}/manifest")
async def get_manifest_endpoint(workspace_id: str):
    try:
        return await codex_get_manifest(workspace_id)
    except Exception as e:
        logger.error(f"Codex get_manifest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/codex/workspaces/{workspace_id}/file")
async def read_file_endpoint(workspace_id: str, path: str = Query(..., alias="relative_path")):
    try:
        return await codex_read_file(workspace_id, path)
    except Exception as e:
        logger.error(f"Codex read_file failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
