"""
CLI MCP Server — safe, scoped system tools for Osoba task planning.

Security model:
- No raw command passthrough; all commands are hardcoded server-side
- File arguments validated against real directory contents at runtime
- All paths constructed server-side; LLM never supplies raw filesystem paths
- Directory scopes are a hardcoded allowlist; only scope keys are accepted
- Service names validated against CLI_ALLOWED_SERVICES env var
- All output truncated to CLI_MAX_OUTPUT_CHARS
- read_workspace_file denies hidden files and sensitive extensions/filenames
- read_log enforces a hard byte cap before reading to bound memory use
"""

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Path setup — derived from this file's location (backend/server_cli.py)
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent.resolve()          # backend/
LOGS_DIR = _HERE / "logs"
SCRIPTS_DIR = _HERE / "scripts"
ARTIFACTS_DIR = (_HERE.parent / "artifacts").resolve()  # repo root / artifacts

# ---------------------------------------------------------------------------
# Tunables from environment
# ---------------------------------------------------------------------------
MAX_OUTPUT_CHARS: int = int(os.getenv("CLI_MAX_OUTPUT_CHARS", "5000"))
_MAX_LOG_LINES: int = 500        # hard cap regardless of caller request
_MIN_LOG_LINES: int = 1
_MAX_DIR_ENTRIES: int = 200
# Byte cap applied before reading log lines — prevents loading huge files into memory.
# Tail is read from the end of this window, so recent lines are always preserved.
_MAX_LOG_READ_BYTES: int = int(os.getenv("CLI_MAX_LOG_READ_BYTES", str(2 * 1024 * 1024)))  # 2 MB

# ---------------------------------------------------------------------------
# read_workspace_file — content sensitivity controls
# ---------------------------------------------------------------------------
# Extensions whose content is denied regardless of location.
_DENIED_EXTENSIONS: frozenset[str] = frozenset({
    ".env", ".pem", ".key", ".p12", ".pfx", ".jks", ".crt", ".cer",
    ".der", ".ppk", ".keystore", ".secret", ".secrets",
})
# Exact filenames (lowercased) that are always denied.
_DENIED_FILENAMES: frozenset[str] = frozenset({
    ".env", "credentials.json", "credentials.yaml", "credentials.yml",
    "secrets.json", "secrets.yaml", "secrets.yml",
    "service_account.json", "id_rsa", "id_ed25519", "id_ecdsa",
    ".netrc", ".pgpass",
})

# Services allowed for status checks. Empty → service_status always errors.
# Set CLI_ALLOWED_SERVICES=kiosk,nginx in .env to enable.
_raw_services = os.getenv("CLI_ALLOWED_SERVICES", "")
ALLOWED_SERVICES: frozenset[str] = frozenset(
    s.strip() for s in _raw_services.split(",") if s.strip()
)

# ---------------------------------------------------------------------------
# Scope map — the only directories the LLM may inspect
# ---------------------------------------------------------------------------
SCOPE_MAP: dict[str, Path] = {
    "artifacts": ARTIFACTS_DIR,
    "logs": LOGS_DIR,
    "scripts": SCRIPTS_DIR,
}

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="CLIServer",
    version="1.0.0",
    instructions=(
        "Provides safe, scoped system tools for diagnostics and file inspection. "
        "No raw command execution. All paths and service names are validated server-side."
    ),
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _truncate(text: str) -> str:
    """Truncate output to MAX_OUTPUT_CHARS, keeping the tail (most recent content)."""
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return f"[truncated — showing last {MAX_OUTPUT_CHARS} chars]\n" + text[-MAX_OUTPUT_CHARS:]


def _safe_name(name: str) -> bool:
    """Return True only if name is a plain filename with no path components."""
    if not name:
        return False
    # Reject any path separator or traversal sequences
    return "/" not in name and "\\" not in name and ".." not in name and "\x00" not in name


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_system_health() -> dict:
    """
    Returns structured system health information: disk usage, platform, uptime.
    No arguments required. Safe — no user input reaches the OS.
    """
    # Disk
    try:
        usage = shutil.disk_usage("/")
        disk = {
            "total_gb": round(usage.total / 1e9, 2),
            "used_gb": round(usage.used / 1e9, 2),
            "free_gb": round(usage.free / 1e9, 2),
            "used_pct": round(usage.used / usage.total * 100, 1),
        }
    except Exception as exc:
        disk = {"error": str(exc)}

    # Uptime — hardcoded command, no user input
    uptime: str | None = None
    try:
        proc = subprocess.run(
            ["uptime", "-p"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            uptime = proc.stdout.strip()
    except Exception:
        pass  # uptime is informational; silently omit on failure

    return {
        "platform": platform.system(),
        "node": platform.node(),
        "release": platform.release(),
        "disk": disk,
        "uptime": uptime,
    }


@mcp.tool()
async def list_dir(scope: Literal["artifacts", "logs", "scripts"]) -> dict:
    """
    Lists contents of an allowed directory scope.

    Args:
        scope: One of 'artifacts', 'logs', or 'scripts'. No filesystem paths accepted.

    Returns:
        Structured listing with name, type, and size for each entry.
    """
    if scope not in SCOPE_MAP:
        return {"error": f"Invalid scope '{scope}'. Allowed: {sorted(SCOPE_MAP.keys())}"}

    target = SCOPE_MAP[scope]
    if not target.exists():
        return {"error": f"Directory for scope '{scope}' does not exist at {target}"}

    try:
        entries = []
        for entry in sorted(target.iterdir()):
            stat = entry.stat()
            entries.append({
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "size_bytes": stat.st_size if entry.is_file() else None,
            })
        return {
            "scope": scope,
            "entry_count": len(entries),
            "entries": entries[:_MAX_DIR_ENTRIES],
        }
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
async def read_log(name: str, lines: int = 100) -> dict:
    """
    Reads the last N lines of a named log file from the logs directory.

    Args:
        name: Filename only (e.g. 'mcp_backend.log'). No paths or traversal.
        lines: Number of tail lines to return. Clamped to 1–500.

    Returns:
        Structured dict with content, lines_returned, and total_lines.
    """
    if not _safe_name(name):
        return {"error": "Invalid log name. Provide a plain filename with no path separators."}

    # Validate against actual files on disk — never trust the name alone
    try:
        available = {f.name for f in LOGS_DIR.iterdir() if f.is_file()}
    except Exception as exc:
        return {"error": f"Could not read logs directory: {exc}"}

    if name not in available:
        return {"error": f"Log '{name}' not found.", "available": sorted(available)}

    lines = max(_MIN_LOG_LINES, min(lines, _MAX_LOG_LINES))
    log_path = LOGS_DIR / name

    try:
        file_size = log_path.stat().st_size
        with log_path.open("rb") as fh:
            # Read only the tail window to bound memory use on large log files.
            if file_size > _MAX_LOG_READ_BYTES:
                fh.seek(-_MAX_LOG_READ_BYTES, 2)  # seek from end
                raw = fh.read()
                # Drop the first (likely partial) line created by the mid-file seek.
                raw = raw[raw.find(b"\n") + 1:]
                byte_capped = True
            else:
                raw = fh.read()
                byte_capped = False
        all_lines = raw.decode("utf-8", errors="replace").splitlines(keepends=True)
        tail = all_lines[-lines:]
        content = "".join(tail)
        return {
            "name": name,
            "lines_requested": lines,
            "lines_returned": len(tail),
            "total_lines": len(all_lines),
            "byte_capped": byte_capped,
            "content": _truncate(content),
        }
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
async def service_status(name: str) -> dict:
    """
    Returns systemd service status for an explicitly allowlisted service.

    Args:
        name: Service name. Must be in the CLI_ALLOWED_SERVICES env var list.

    Returns:
        Structured dict: service, status, active_state, sub_state, description.
    """
    if not ALLOWED_SERVICES:
        return {
            "error": (
                "No services configured. "
                "Set CLI_ALLOWED_SERVICES=service1,service2 in the environment."
            )
        }

    if not _safe_name(name) or name not in ALLOWED_SERVICES:
        return {"error": f"Service '{name}' is not in the allowed services list."}

    if platform.system() != "Linux":
        return {
            "error": f"systemctl not available on {platform.system()}. "
                     "This tool requires a Linux system."
        }

    try:
        is_active = subprocess.run(
            ["systemctl", "is-active", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        active_state = is_active.stdout.strip()

        show = subprocess.run(
            [
                "systemctl", "show", name,
                "--property=ActiveState,SubState,Description,MainPID",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        props: dict[str, str] = {}
        for line in show.stdout.strip().splitlines():
            if "=" in line:
                key, _, val = line.partition("=")
                props[key] = val

        return {
            "service": name,
            "status": active_state,
            "active_state": props.get("ActiveState"),
            "sub_state": props.get("SubState"),
            "description": props.get("Description"),
            "main_pid": props.get("MainPID"),
        }
    except subprocess.TimeoutExpired:
        return {"error": "systemctl timed out after 5 seconds"}
    except FileNotFoundError:
        return {"error": "systemctl binary not found on this system"}
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
async def read_workspace_file(path_within_scope: str) -> dict:
    """
    Reads a file from within the artifacts directory (Codex workspaces, task outputs).

    Args:
        path_within_scope: Relative path within the artifacts directory.
                           Path traversal (../) is rejected.

    Returns:
        Structured dict with content (truncated to CLI_MAX_OUTPUT_CHARS) and metadata.
    """
    if not path_within_scope or not path_within_scope.strip():
        return {"error": "path_within_scope is required"}

    # Reject obvious traversal patterns before resolving
    if ".." in path_within_scope or path_within_scope.startswith("/"):
        return {"error": "Path traversal not permitted. Use a relative path within the artifacts directory."}

    try:
        candidate = (ARTIFACTS_DIR / path_within_scope).resolve()
        artifacts_resolved = ARTIFACTS_DIR.resolve()
    except Exception:
        return {"error": "Invalid path"}

    # Enforce containment: resolved path must be under artifacts dir
    try:
        candidate.relative_to(artifacts_resolved)
    except ValueError:
        return {"error": "Path traversal not permitted. Path must be within the artifacts directory."}

    if not candidate.exists():
        return {"error": f"File not found: {path_within_scope}"}

    if not candidate.is_file():
        return {"error": f"Path is not a file: {path_within_scope}"}

    # Deny hidden files (any path component starting with '.')
    if any(part.startswith(".") for part in candidate.parts):
        return {"error": "Access denied: hidden files are not readable."}

    # Deny by filename (case-insensitive exact match)
    if candidate.name.lower() in _DENIED_FILENAMES:
        return {"error": f"Access denied: '{candidate.name}' is a restricted filename."}

    # Deny by extension (all suffixes, e.g. .tar.gz → check both .gz and .tar.gz)
    for suffix in candidate.suffixes:
        if suffix.lower() in _DENIED_EXTENSIONS:
            return {"error": f"Access denied: '{suffix}' files are restricted."}

    try:
        content = candidate.read_text(errors="replace")
        return {
            "path": path_within_scope,
            "size_bytes": candidate.stat().st_size,
            "content": _truncate(content),
            "truncated": len(content) > MAX_OUTPUT_CHARS,
        }
    except Exception as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    mcp.run()
