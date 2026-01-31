import asyncio
from typing import Any, Dict, Optional

from core.config import CODEX_SERVICE_NAME, get_logger
from services.mcp_service import submit_mcp_request, wait_mcp_response
from db.settings_crud import get_provider_api_key
from core.config import CODEX_DEBUG

logger = get_logger("codex_client")


def _normalize_workspace_data(raw: Any) -> Dict[str, Any]:
    """Normalize FastMCP tool response (often a list of text blocks) into a dict.
    Expects server_codex.create_workspace() result; falls back to parsing strings.
    """
    if isinstance(raw, dict):
        return raw
    # FastMCP wraps tool results into a list of blocks: [{type:'text', content:'...'}]
    if isinstance(raw, list) and raw:
        for blk in raw:
            try:
                if isinstance(blk, dict) and blk.get('type') == 'text' and isinstance(blk.get('content'), str):
                    txt = blk['content']
                    # Try JSON first
                    import json, ast, re
                    try:
                        return json.loads(txt)
                    except Exception:
                        pass
                    # Try python-literal dict
                    try:
                        val = ast.literal_eval(txt)
                        if isinstance(val, dict):
                            return val
                    except Exception:
                        pass
                    # Fallback: extract workspace_path and synthesize id
                    m = re.search(r"\.codex_workspaces/([^/\n\r]+)", txt)
                    d: Dict[str, Any] = {}
                    if m:
                        d['workspace_id'] = m.group(1)
                        d['workspace_path'] = txt
                    if d:
                        return d
            except Exception:
                continue
    # Unknown shape; return empty to let caller handle
    return {}


async def create_workspace(name_hint: str, keep: bool = False) -> Dict[str, Any]:
    req_id = await submit_mcp_request(CODEX_SERVICE_NAME, "tool", {
        "tool": "create_workspace",
        "params": {"name_hint": name_hint, "keep": bool(keep)}
    })
    resp = await wait_mcp_response(CODEX_SERVICE_NAME, req_id, timeout=30)
    if resp.get("status") == "error":
        raise RuntimeError(resp.get("error"))
    data = resp.get("data")
    norm = _normalize_workspace_data(data)
    return norm


async def start_run(workspace_id: str, instruction: str, model: Optional[str] = None, timeout_seconds: int = 900) -> Dict[str, Any]:
    # Fetch OpenAI API key (gated)
    api_key = get_provider_api_key("openai")
    if not api_key:
        raise RuntimeError("OpenAI API key is required to run Codex")
    params = {
        "workspace_id": workspace_id,
        "instruction": instruction,
        "json_events": True,
        "timeout_seconds": int(timeout_seconds),
        "openai_api_key": api_key,
    }
    if model:
        params["model"] = model
    req_id = await submit_mcp_request(CODEX_SERVICE_NAME, "tool", {
        "tool": "start_codex_run",
        "params": params,
    })
    resp = await wait_mcp_response(CODEX_SERVICE_NAME, req_id, timeout=30)
    if resp.get("status") == "error":
        raise RuntimeError(resp.get("error"))
    data = resp.get("data")
    if CODEX_DEBUG:
        try:
            logger.info(f"[CODEX_CLIENT] start_run raw type={type(data).__name__}")
        except Exception:
            pass
    norm = _normalize_workspace_data(data)  # reuse JSON/text parsing; start_run returns a dict JSON too
    # If parser didn't convert (e.g., direct dict or list), attempt JSON from first block
    if not norm:
        if isinstance(data, dict):
            norm = data
        elif isinstance(data, list) and data:
            try:
                txt = (data[0] or {}).get('content') if isinstance(data[0], dict) else str(data[0])
                import json
                norm = json.loads(txt)
            except Exception:
                norm = { 'raw': data }
    return norm


async def get_run_status(run_id: str, timeout: int = 30) -> Dict[str, Any]:
    req_id = await submit_mcp_request(CODEX_SERVICE_NAME, "tool", {
        "tool": "get_codex_run",
        "params": {"run_id": run_id},
    })
    resp = await wait_mcp_response(CODEX_SERVICE_NAME, req_id, timeout=timeout)
    if resp.get("status") == "error":
        raise RuntimeError(resp.get("error"))
    data = resp.get("data")
    if CODEX_DEBUG:
        try:
            logger.info(f"[CODEX_CLIENT] get_run_status raw type={type(data).__name__}")
        except Exception:
            pass
    # Parse list-of-text into JSON
    if isinstance(data, list) and data:
        txt = (data[0] or {}).get('content') if isinstance(data[0], dict) else str(data[0])
        # Try JSON first
        try:
            import json
            parsed = json.loads(txt)
            return parsed
        except Exception:
            pass
        # Try python literal dict
        try:
            import ast
            parsed = ast.literal_eval(txt)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        # Fallback
        return { 'run': {}, 'raw': data }
    if isinstance(data, dict):
        return data
    return { 'run': {} }


async def cancel_run(run_id: str) -> Dict[str, Any]:
    req_id = await submit_mcp_request(CODEX_SERVICE_NAME, "tool", {
        "tool": "cancel_codex_run",
        "params": {"run_id": run_id},
    })
    resp = await wait_mcp_response(CODEX_SERVICE_NAME, req_id, timeout=20)
    if resp.get("status") == "error":
        raise RuntimeError(resp.get("error"))
    return resp.get("data") or {}


async def get_manifest(workspace_id: str) -> Dict[str, Any]:
    req_id = await submit_mcp_request(CODEX_SERVICE_NAME, "tool", {
        "tool": "get_manifest",
        "params": {"workspace_id": workspace_id},
    })
    resp = await wait_mcp_response(CODEX_SERVICE_NAME, req_id, timeout=20)
    if resp.get("status") == "error":
        raise RuntimeError(resp.get("error"))
    data = resp.get("data")
    if isinstance(data, list) and data:
        try:
            txt = (data[0] or {}).get('content') if isinstance(data[0], dict) else str(data[0])
            import json
            parsed = json.loads(txt)
            return parsed
        except Exception:
            return { 'manifest': {}, 'raw': data }
    if isinstance(data, dict):
        return data
    return { 'manifest': {} }


async def read_file(workspace_id: str, relative_path: str) -> Dict[str, Any]:
    req_id = await submit_mcp_request(CODEX_SERVICE_NAME, "tool", {
        "tool": "read_file",
        "params": {"workspace_id": workspace_id, "relative_path": relative_path},
    })
    resp = await wait_mcp_response(CODEX_SERVICE_NAME, req_id, timeout=20)
    if resp.get("status") == "error":
        raise RuntimeError(resp.get("error"))
    data = resp.get("data")
    if isinstance(data, list) and data:
        try:
            txt = (data[0] or {}).get('content') if isinstance(data[0], dict) else str(data[0])
            import json
            parsed = json.loads(txt)
            return parsed
        except Exception:
            return { 'status': 'error', 'message': 'Could not parse file content', 'raw': data }
    if isinstance(data, dict):
        return data
    return { 'status': 'error', 'message': 'Invalid file response' }
