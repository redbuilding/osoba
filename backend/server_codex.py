# mcp_codex_workspace_server.py
"""
FastMCP server to create isolated workspaces and run Codex CLI within them.

Security posture (defense-in-depth):
- Dedicated per-task workspace directory
- Isolated HOME under workspace so Codex won't read your real ~/.codex
- Refuse symlinks in workspace (common escape vector)
- Strict realpath-based path containment checks for read operations
- Optional output policy enforcement after Codex run:
    - allowed extensions allowlist
    - dotfile blocking (except optional allowlist)
    - max files
    - max total output bytes
    - block binary-like files (simple heuristic)

Important note:
- Strongest isolation still comes from OS/container sandboxing (e.g., Docker with --network=none).
  This MCP server is designed to be compatible with that deployment without changes.
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import find_dotenv, load_dotenv

from mcp.server.fastmcp import FastMCP

# -----------------------------
# Logging (matches your style)
# -----------------------------
script_logger = logging.getLogger("server_codex_script")
script_logger.setLevel(logging.INFO)
if not script_logger.hasHandlers():
    stderr_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [SERVER_CODEX] %(message)s"
    )
    stderr_handler.setFormatter(formatter)
    script_logger.addHandler(stderr_handler)
    script_logger.propagate = False

script_logger.info(f"Script starting. Python Executable: {sys.executable}")
script_logger.info(f"Current Working Directory (CWD): {os.getcwd()}")


# -----------------------------
# Env / dotenv
# -----------------------------
dotenv_path = find_dotenv(usecwd=False, raise_error_if_not_found=False)
if dotenv_path:
    script_logger.info(f"Loading .env file from: {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    script_logger.warning(
        "No .env file found by find_dotenv(). Relying on default load_dotenv() or existing env vars."
    )
    load_dotenv()

CODEX_BIN = os.getenv("CODEX_BIN", "codex")
WORKSPACES_DIR = Path(
    os.getenv("CODEX_WORKSPACES_DIR", "./.codex_workspaces")
).resolve()

# Hard limits / defaults
MAX_PROMPT_CHARS = int(os.getenv("CODEX_MAX_PROMPT_CHARS", "20000"))
MAX_STDOUT_CHARS = int(os.getenv("CODEX_MAX_STDOUT_CHARS", "200000"))
MAX_STDERR_CHARS = int(os.getenv("CODEX_MAX_STDERR_CHARS", "50000"))
MAX_FILES_IN_MANIFEST = int(os.getenv("CODEX_MAX_FILES_IN_MANIFEST", "5000"))
MAX_FILE_BYTES_READ = int(os.getenv("CODEX_MAX_FILE_BYTES_READ", "200000"))

# Output policy defaults
DEFAULT_ALLOWED_EXTS = {
    ".html",
    ".css",
    ".js",
    ".json",
    ".md",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".ico",
}
DEFAULT_BLOCK_DOTFILES = True
DEFAULT_ALLOWED_DOTFILES = {".gitignore"}  # add more if you want
DEFAULT_MAX_OUTPUT_FILES = int(os.getenv("CODEX_MAX_OUTPUT_FILES", "500"))
DEFAULT_MAX_OUTPUT_TOTAL_BYTES = int(
    os.getenv("CODEX_MAX_OUTPUT_TOTAL_BYTES", str(20 * 1024 * 1024))
)  # 20MB

script_logger.info(f"CODEX_BIN={CODEX_BIN}")
script_logger.info(f"WORKSPACES_DIR={WORKSPACES_DIR}")


# -----------------------------
# FastMCP server
# -----------------------------
mcp = FastMCP(
    name="CodexWorkspaceServer",
    version="0.2.0",
    display_name="Codex Workspace Server",
    description=(
        "Creates isolated workspaces and runs Codex CLI in a bounded directory "
        "for later human review."
    ),
)
script_logger.info("FastMCP instance created.")


# -----------------------------
# Helpers
# -----------------------------
def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _trim(s: str, limit: int) -> str:
    if not s:
        return ""
    if len(s) <= limit:
        return s
    return s[:limit] + "\n...[truncated]..."


def _workspace_root(workspace_id: str) -> Path:
    return (WORKSPACES_DIR / workspace_id).resolve()


def _realpath_strict(p: Path) -> Path:
    """
    Resolve symlinks and normalize path. If path doesn't exist, resolve parent strictly if possible.
    """
    try:
        return p.resolve(strict=True)
    except FileNotFoundError:
        # resolve as much as possible
        parent = p.parent
        try:
            parent_r = parent.resolve(strict=True)
            return (parent_r / p.name).resolve()
        except FileNotFoundError:
            return p.resolve()


def _is_within(root: Path, target: Path) -> bool:
    """
    True if target is within root after resolving (realpath) to avoid traversal/symlink tricks.
    """
    root_r = _realpath_strict(root)
    target_r = _realpath_strict(target)
    try:
        target_r.relative_to(root_r)
        return True
    except ValueError:
        return False


def _reject_symlinks_under(root: Path) -> List[str]:
    """
    Return list of symlink paths found under root (relative).
    """
    bad = []
    for p in root.rglob("*"):
        try:
            if p.is_symlink():
                bad.append(str(p.relative_to(root)))
        except OSError:
            bad.append(str(p.relative_to(root)))
    return bad


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _looks_binary(p: Path, max_probe: int = 4096) -> bool:
    """
    Simple heuristic: if NUL bytes appear early, treat as binary.
    """
    try:
        with p.open("rb") as f:
            chunk = f.read(max_probe)
        return b"\x00" in chunk
    except OSError:
        return False


def _make_isolated_home(workspace_root: Path) -> Path:
    """
    Create isolated HOME directory under workspace.
    """
    home_dir = workspace_root / ".home"
    _ensure_dir(home_dir / ".codex" / "rules")
    return home_dir


def _write_codex_rules(home_dir: Path, rules_name: str = "default.rules") -> Path:
    """
    Defense-in-depth rules file. Don't rely on this as the only boundary.
    """
    rules_dir = home_dir / ".codex" / "rules"
    _ensure_dir(rules_dir)
    rules_path = rules_dir / rules_name

    # These are conservative blocks for common exfil/network and shell spawning.
    # Prefer allowlisting at the orchestrator boundary as well.
    rules_text = """\
# Codex execpolicy rules (defense-in-depth)
# Block common network/exfil and shell spawning.

prefix_rule(pattern=["curl"], decision="block", justification="No outbound network")
prefix_rule(pattern=["wget"], decision="block", justification="No outbound network")
prefix_rule(pattern=["ssh"], decision="block", justification="No remote shells")
prefix_rule(pattern=["scp"], decision="block", justification="No file exfiltration")
prefix_rule(pattern=["rsync"], decision="block", justification="No file sync exfiltration")
prefix_rule(pattern=["nc"], decision="block", justification="No network sockets")
prefix_rule(pattern=["netcat"], decision="block", justification="No network sockets")

prefix_rule(pattern=["bash"], decision="block", justification="No shell spawning")
prefix_rule(pattern=["sh"], decision="block", justification="No shell spawning")
prefix_rule(pattern=["zsh"], decision="block", justification="No shell spawning")
prefix_rule(pattern=["sudo"], decision="block", justification="No privilege escalation")
"""
    rules_path.write_text(rules_text, encoding="utf-8")
    return rules_path


def _build_manifest(workspace_root: Path) -> Dict[str, Any]:
    """
    Deterministic manifest for human review: file list + hashes.
    Excludes internal .home directory and symlinks.
    """
    files: List[Dict[str, Any]] = []
    count = 0
    for p in workspace_root.rglob("*"):
        if count >= MAX_FILES_IN_MANIFEST:
            break
        if p.is_dir():
            continue
        if ".home" in p.parts:
            continue
        try:
            if p.is_symlink():
                continue
        except OSError:
            continue

        rel = str(p.relative_to(workspace_root))
        try:
            st = p.stat()
            files.append(
                {
                    "path": rel,
                    "bytes": st.st_size,
                    "mtime_ms": int(st.st_mtime * 1000),
                    "sha256": _sha256_file(p),
                }
            )
        except OSError:
            files.append({"path": rel, "error": "stat_or_read_failed"})
        count += 1

    return {
        "workspace": str(workspace_root),
        "generated_at_ms": _now_ms(),
        "file_count": len(files),
        "files": files,
        "truncated": len(files) >= MAX_FILES_IN_MANIFEST,
    }


def _evaluate_output_policy(
    workspace_root: Path,
    allowed_exts: set,
    block_dotfiles: bool,
    allowed_dotfiles: set,
    max_output_files: int,
    max_total_bytes: int,
    block_binaries: bool = True,
) -> Dict[str, Any]:
    """
    Evaluate post-run output policy on workspace contents (excluding internal .home).
    Returns violations and summary.
    """
    violations: List[Dict[str, Any]] = []
    total_bytes = 0
    file_count = 0

    for p in workspace_root.rglob("*"):
        if p.is_dir():
            continue
        if ".home" in p.parts:
            continue
        try:
            if p.is_symlink():
                violations.append(
                    {
                        "type": "symlink_present",
                        "path": str(p.relative_to(workspace_root)),
                    }
                )
                continue
        except OSError:
            violations.append(
                {
                    "type": "symlink_check_failed",
                    "path": str(p.relative_to(workspace_root)),
                }
            )
            continue

        rel = str(p.relative_to(workspace_root))
        name = p.name

        # dotfiles policy (only for top-level dotfiles or any path segment starting with '.')
        if block_dotfiles:
            parts = p.relative_to(workspace_root).parts
            has_dot_segment = any(seg.startswith(".") for seg in parts)
            if has_dot_segment:
                # allow internal .home already excluded; allow explicit exceptions
                if name not in allowed_dotfiles:
                    violations.append({"type": "dotfile_blocked", "path": rel})

        ext = p.suffix.lower()
        if ext and allowed_exts and ext not in allowed_exts:
            violations.append({"type": "disallowed_extension", "path": rel, "ext": ext})

        try:
            st = p.stat()
            total_bytes += st.st_size
            file_count += 1
        except OSError:
            violations.append({"type": "stat_failed", "path": rel})

        if block_binaries and _looks_binary(p):
            # allow common image types even though they are binary
            if ext not in {".png", ".jpg", ".jpeg", ".svg", ".ico"}:
                violations.append({"type": "binary_file_blocked", "path": rel})

        if file_count > max_output_files:
            violations.append(
                {
                    "type": "too_many_files",
                    "limit": max_output_files,
                    "count": file_count,
                }
            )
            break

        if total_bytes > max_total_bytes:
            violations.append(
                {
                    "type": "too_much_output",
                    "limit_bytes": max_total_bytes,
                    "total_bytes": total_bytes,
                }
            )
            break

    return {
        "ok": len(violations) == 0,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "violations": violations,
    }


async def _run_subprocess(
    cmd: List[str],
    cwd: Path,
    env: Dict[str, str],
    timeout_seconds: int,
) -> subprocess.CompletedProcess:
    """
    Run blocking subprocess without blocking the event loop.
    """

    def _blocking():
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=max(1, timeout_seconds),
        )

    return await asyncio.to_thread(_blocking)


async def _create_venv(root: Path) -> Tuple[bool, str]:
    """
    Create python venv in workspace using server-side python.
    Returns (ok, message).
    """
    py = shutil.which("python3") or shutil.which("python") or "python"
    cmd = [py, "-m", "venv", str(root / ".venv")]
    try:
        proc = await _run_subprocess(
            cmd, cwd=root, env=os.environ.copy(), timeout_seconds=120
        )
        if proc.returncode == 0:
            return True, "venv created"
        return False, _trim(proc.stderr or proc.stdout or "venv creation failed", 2000)
    except Exception as e:
        return False, str(e)


# -----------------------------
# Tools
# -----------------------------
@mcp.tool()
async def create_workspace(
    name_hint: str = "task",
    make_venv: bool = False,
    allowed_exts: Optional[List[str]] = None,
    block_dotfiles: bool = DEFAULT_BLOCK_DOTFILES,
    allowed_dotfiles: Optional[List[str]] = None,
) -> dict:
    """
    Create a disposable workspace directory for Codex outputs.

    Returns a policy object that the app can use for UI + review gating.
    """
    _ensure_dir(WORKSPACES_DIR)

    safe_hint = (
        "".join(ch for ch in name_hint.lower() if ch.isalnum() or ch in ("-", "_"))[:24]
        or "task"
    )
    workspace_id = f"{safe_hint}-{int(time.time())}-{os.getpid()}"
    root = _workspace_root(workspace_id)
    _ensure_dir(root)

    # Isolated HOME and rules
    home_dir = _make_isolated_home(root)
    rules_path = _write_codex_rules(home_dir)

    # Optional venv (created by server, not by Codex)
    venv_result = None
    if make_venv:
        ok, msg = await _create_venv(root)
        venv_result = {"ok": ok, "message": msg}

    # Write a simple review README
    (root / "README_FOR_REVIEW.md").write_text(
        "# Workspace output\n\n"
        "This folder was generated by Codex CLI inside a restricted workspace.\n"
        "Review changes before promoting them.\n",
        encoding="utf-8",
    )

    policy_exts = set(allowed_exts) if allowed_exts else set(DEFAULT_ALLOWED_EXTS)
    policy_dot_allow = (
        set(allowed_dotfiles)
        if allowed_dotfiles is not None
        else set(DEFAULT_ALLOWED_DOTFILES)
    )

    script_logger.info(f"Created workspace {workspace_id} at {root}")

    return {
        "status": "success",
        "workspace_id": workspace_id,
        "workspace_path": str(root),
        "isolated_home": str(home_dir),
        "codex_rules_path": str(rules_path),
        "venv": venv_result,
        "policy": {
            "allowed_exts": sorted(policy_exts),
            "block_dotfiles": bool(block_dotfiles),
            "allowed_dotfiles": sorted(policy_dot_allow),
            "max_output_files_default": DEFAULT_MAX_OUTPUT_FILES,
            "max_output_total_bytes_default": DEFAULT_MAX_OUTPUT_TOTAL_BYTES,
            "notes": [
                "Codex is intended to only read/write inside this workspace.",
                "For strongest isolation, run this server + Codex in a container/VM with no network.",
            ],
        },
    }


@mcp.tool()
async def run_codex_task(
    workspace_id: str,
    instruction: str,
    model: Optional[str] = None,
    sandbox: str = "workspace-write",
    approval: str = "never",
    json_events: bool = True,
    timeout_seconds: int = 900,
    # Policy enforcement toggles (post-run)
    enforce_output_policy: bool = True,
    allowed_exts: Optional[List[str]] = None,
    block_dotfiles: bool = DEFAULT_BLOCK_DOTFILES,
    allowed_dotfiles: Optional[List[str]] = None,
    max_output_files: int = DEFAULT_MAX_OUTPUT_FILES,
    max_output_total_bytes: int = DEFAULT_MAX_OUTPUT_TOTAL_BYTES,
    block_binaries: bool = True,
) -> dict:
    """
    Run Codex CLI inside the given workspace and return logs + a review manifest.

    Security features:
    - Sets --cd to workspace root
    - Isolated HOME under workspace to avoid using real ~/.codex
    - Refuses symlinks already present in workspace
    - Optional post-run output policy enforcement (recommended)
    """
    if not instruction or len(instruction) > MAX_PROMPT_CHARS:
        return {
            "status": "error",
            "message": f"instruction must be 1..{MAX_PROMPT_CHARS} chars",
        }

    root = _workspace_root(workspace_id)
    if not root.exists():
        return {"status": "error", "message": "workspace not found"}

    # Hard refusal if workspace contains symlinks (escape vector)
    syms = _reject_symlinks_under(root)
    if syms:
        return {
            "status": "error",
            "message": "workspace contains symlinks; refusing to run",
            "symlinks": syms[:50],
        }

    # Setup isolated HOME and rules (defense-in-depth)
    home_dir = _make_isolated_home(root)
    _write_codex_rules(home_dir)

    cmd = [
        CODEX_BIN,
        "exec",
        "--cd",
        str(root),
        "--skip-git-repo-check",
        "--sandbox",
        sandbox,
    ]
    if model:
        cmd += ["--model", model]
    if json_events:
        cmd += ["--json"]

    # prompt
    cmd += [instruction]

    env = os.environ.copy()
    env["HOME"] = str(home_dir)
    env["USERPROFILE"] = str(home_dir)

    started = _now_ms()
    script_logger.info(
        f"Running Codex in workspace {workspace_id} sandbox={sandbox} approval={approval} json={json_events}"
    )

    events_jsonl = ""
    try:
        proc = await _run_subprocess(
            cmd, cwd=root, env=env, timeout_seconds=timeout_seconds
        )
        exit_code = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        # If --json, stdout will typically be JSONL events; keep full (trimmed) copy for UI parsing/storage
        if json_events:
            events_jsonl = _trim(stdout, MAX_STDOUT_CHARS)
            stdout_tail = _trim(stdout, MAX_STDOUT_CHARS)[-50_000:]
        else:
            stdout_tail = _trim(stdout, MAX_STDOUT_CHARS)[-50_000:]

        stderr_tail = _trim(stderr, MAX_STDERR_CHARS)[-20_000:]

    except subprocess.TimeoutExpired:
        exit_code = 124
        stdout_tail = ""
        stderr_tail = "Codex run timed out"
    except FileNotFoundError:
        return {"status": "error", "message": f"codex binary not found: {CODEX_BIN}"}
    except Exception as e:
        script_logger.exception("Unexpected error running Codex")
        return {"status": "error", "message": str(e)}

    # Build manifest for review (always)
    manifest = _build_manifest(root)

    # Output policy enforcement (recommended)
    policy_result = None
    if enforce_output_policy:
        policy_exts = set(allowed_exts) if allowed_exts else set(DEFAULT_ALLOWED_EXTS)
        policy_dot_allow = (
            set(allowed_dotfiles)
            if allowed_dotfiles is not None
            else set(DEFAULT_ALLOWED_DOTFILES)
        )
        policy_result = _evaluate_output_policy(
            workspace_root=root,
            allowed_exts=policy_exts,
            block_dotfiles=block_dotfiles,
            allowed_dotfiles=policy_dot_allow,
            max_output_files=max_output_files,
            max_total_bytes=max_output_total_bytes,
            block_binaries=block_binaries,
        )

    finished = _now_ms()

    # If policy fails, still "successfully ran", but mark needs attention
    needs_attention = bool(policy_result and not policy_result.get("ok", True))

    return {
        "status": "success",
        "workspace_id": workspace_id,
        "workspace_path": str(root),
        "started_at_ms": started,
        "finished_at_ms": finished,
        "duration_ms": finished - started,
        "exit_code": exit_code,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "events_jsonl": events_jsonl if json_events else "",
        "manifest": manifest,
        "output_policy": policy_result,
        "review_required": True,
        "needs_attention": needs_attention,
        "security_notes": [
            "HOME is isolated under workspace/.home to avoid using your real ~/.codex.",
            "Symlinks are refused to reduce workspace escape risk.",
            "For strongest isolation, run this server + Codex in a container/VM with no network.",
        ],
    }


@mcp.tool()
async def read_file(workspace_id: str, relative_path: str) -> dict:
    """
    Read a file for review; refuses escapes, symlinks, and large files.
    """
    root = _workspace_root(workspace_id)
    if not root.exists():
        return {"status": "error", "message": "workspace not found"}

    # Normalize & check containment
    target = root / relative_path
    if not _is_within(root, target):
        return {"status": "error", "message": "path escapes workspace; refused"}

    target_r = _realpath_strict(target)

    # Refuse symlink targets
    try:
        if target_r.is_symlink():
            return {"status": "error", "message": "symlink refused"}
    except OSError:
        return {"status": "error", "message": "symlink check failed; refused"}

    if not target_r.exists() or not target_r.is_file():
        return {"status": "error", "message": "file not found"}

    size = target_r.stat().st_size
    if size > MAX_FILE_BYTES_READ:
        return {
            "status": "error",
            "message": "file too large to read via tool",
            "bytes": size,
        }

    content = target_r.read_text(encoding="utf-8", errors="replace")
    return {
        "status": "success",
        "path": relative_path,
        "bytes": size,
        "content": content,
    }


@mcp.tool()
async def get_manifest(workspace_id: str) -> dict:
    """
    Return the review manifest for the workspace.
    """
    root = _workspace_root(workspace_id)
    if not root.exists():
        return {"status": "error", "message": "workspace not found"}
    return {"status": "success", "manifest": _build_manifest(root)}


@mcp.tool()
async def cleanup_workspace(workspace_id: str) -> dict:
    """
    Delete a workspace. Safety: only deletes under WORKSPACES_DIR.
    """
    root = _workspace_root(workspace_id)
    if not root.exists():
        return {"status": "success", "deleted": False, "message": "not found"}

    # Safety: only delete under base dir
    if not _is_within(WORKSPACES_DIR, root):
        return {
            "status": "error",
            "message": "refused: workspace path not under base dir",
        }

    shutil.rmtree(root, ignore_errors=True)
    return {"status": "success", "deleted": True, "workspace_id": workspace_id}


# No __main__ required when running via fastmcp CLI / your launcher.
if __name__ == "__main__":
    script_logger.info(
        "This FastMCP server is typically run via your FastMCP launcher. "
        "If you run directly, ensure stdio transport is configured by your runner."
    )
