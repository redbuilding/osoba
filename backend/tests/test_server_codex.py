import asyncio
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


def import_codex_with_env(tmpdir: Path):
    os.environ["CODEX_WORKSPACES_DIR"] = str(tmpdir / ".codex_ws_test")
    # Keep concurrency low for tests
    os.environ["CODEX_MAX_CONCURRENCY"] = "1"
    spec = importlib.util.spec_from_file_location("server_codex", str(Path("backend") / "server_codex.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod


@pytest.mark.asyncio
async def test_create_workspace_and_artifacts(tmp_path):
    mod = import_codex_with_env(tmp_path)
    res = await mod.create_workspace(name_hint="testws", keep=True)
    assert res["status"] == "success"
    ws_id = res["workspace_id"]
    root = Path(res["workspace_path"])  # type: ignore
    assert root.exists()
    # artifacts dir + metadata
    art = Path(res["artifacts_path"])  # type: ignore
    assert art.exists()
    meta = json.loads((art / "metadata.json").read_text())
    assert meta.get("keep") is True
    assert res.get("pinned") is True


def _completed(stdout: str, stderr: str = "", code: int = 0):
    return subprocess.CompletedProcess(args=["codex"], returncode=code, stdout=stdout, stderr=stderr)


@pytest.mark.asyncio
async def test_run_codex_task_success_jsonl(tmp_path, monkeypatch):
    mod = import_codex_with_env(tmp_path)
    ws = await mod.create_workspace("ok")
    ws_id = ws["workspace_id"]
    root = Path(ws["workspace_path"])  # type: ignore
    # Create an allowed output file to include in manifest
    (root / "index.html").write_text("<html></html>")

    # JSONL events with success
    events = "\n".join([
        json.dumps({"type": "thread.started"}),
        json.dumps({"type": "turn.started"}),
        json.dumps({"type": "turn.completed"}),
    ])

    async def fake_run(cmd, cwd, env, timeout_seconds):
        return _completed(stdout=events + "\nAuthorization: Bearer XXXXXX", stderr="", code=0)

    monkeypatch.setattr(mod, "_run_subprocess", fake_run)
    out = await mod.run_codex_task(ws_id, "do it", json_events=True)
    assert out["status"] == "success"
    assert out["task_ok"] is True
    # Redacted in tail
    assert "Authorization: Bearer" not in out["stdout_tail"]
    # Artifacts written
    artifacts = Path(out["artifacts"]["manifest_path"])  # type: ignore
    assert artifacts.exists()
    events_path = Path(out["artifacts"]["events_path"])  # type: ignore
    assert events_path.exists()


@pytest.mark.asyncio
async def test_run_codex_task_fail_on_error_event(tmp_path, monkeypatch):
    mod = import_codex_with_env(tmp_path)
    ws = await mod.create_workspace("fail")
    ws_id = ws["workspace_id"]
    events = "\n".join([
        json.dumps({"type": "turn.started"}),
        json.dumps({"type": "error", "message": "boom"}),
    ])

    async def fake_run(cmd, cwd, env, timeout_seconds):
        return _completed(stdout=events, stderr="", code=0)

    monkeypatch.setattr(mod, "_run_subprocess", fake_run)
    out = await mod.run_codex_task(ws_id, "do it", json_events=True)
    assert out["status"] == "failed"
    assert out["task_ok"] is False
    assert "boom" in (out.get("error_message") or "")


@pytest.mark.asyncio
async def test_run_codex_task_incomplete_stream(tmp_path, monkeypatch):
    mod = import_codex_with_env(tmp_path)
    ws = await mod.create_workspace("incomplete")
    ws_id = ws["workspace_id"]
    # only item.* events
    events = "\n".join([json.dumps({"type": "item.log", "message": "x"})])

    async def fake_run(cmd, cwd, env, timeout_seconds):
        return _completed(stdout=events, stderr="", code=0)

    monkeypatch.setattr(mod, "_run_subprocess", fake_run)
    out = await mod.run_codex_task(ws_id, "do it", json_events=True)
    assert out["status"] == "failed"
    assert out["task_ok"] is False
    assert "Incomplete" in (out.get("error_message") or "")


@pytest.mark.asyncio
async def test_run_codex_task_nonzero_exit(tmp_path, monkeypatch):
    mod = import_codex_with_env(tmp_path)
    ws = await mod.create_workspace("nonzero")
    ws_id = ws["workspace_id"]

    async def fake_run(cmd, cwd, env, timeout_seconds):
        return _completed(stdout="", stderr="error", code=2)

    monkeypatch.setattr(mod, "_run_subprocess", fake_run)
    out = await mod.run_codex_task(ws_id, "do it", json_events=False)
    assert out["status"] == "failed"
    assert out["task_ok"] is False
    assert out["exit_code"] == 2


@pytest.mark.asyncio
async def test_output_policy_hard_fail(tmp_path, monkeypatch):
    mod = import_codex_with_env(tmp_path)
    ws = await mod.create_workspace("policy")
    ws_id = ws["workspace_id"]
    root = Path(ws["workspace_path"])  # type: ignore
    # Create a disallowed .py file to trigger hard fail (web profile disallows .py)
    (root / "script.py").write_text("print('x')")
    events = json.dumps({"type": "turn.completed"})

    async def fake_run(cmd, cwd, env, timeout_seconds):
        return _completed(stdout=events, stderr="", code=0)

    monkeypatch.setattr(mod, "_run_subprocess", fake_run)
    out = await mod.run_codex_task(ws_id, "do it", json_events=True)
    assert out["status"] == "failed"
    assert out["task_ok"] is False
    assert out["output_policy"]["hard_fail"] is True


@pytest.mark.asyncio
async def test_cleanup_expired_workspaces(tmp_path):
    mod = import_codex_with_env(tmp_path)
    # Create two workspaces manually
    base = Path(os.environ["CODEX_WORKSPACES_DIR"])  # type: ignore
    base.mkdir(parents=True, exist_ok=True)
    old_ws = base / "old-1"
    old_ws.mkdir(parents=True, exist_ok=True)
    pinned_ws = base / "keep-1"
    pinned_ws.mkdir(parents=True, exist_ok=True)
    (pinned_ws / "codex_artifacts").mkdir(parents=True, exist_ok=True)
    (pinned_ws / "codex_artifacts" / "KEEP").write_text("keep")

    # Set TTL to zero to delete anything not pinned
    mod.RUN_TTL_HOURS = 0
    res = await mod.cleanup_expired_workspaces()
    assert res["status"] == "success"
    # old_ws should be gone, pinned_ws should remain
    assert not old_ws.exists()
    assert pinned_ws.exists()


class FakeProc:
    def __init__(self, stdout_lines: list[str], stderr_lines: list[str], returncode: int = 0):
        self.returncode = returncode
        self._stdout = asyncio.StreamReader()
        self._stderr = asyncio.StreamReader()
        for line in stdout_lines:
            self._stdout.feed_data((line + "\n").encode())
        self._stdout.feed_eof()
        for line in stderr_lines:
            self._stderr.feed_data((line + "\n").encode())
        self._stderr.feed_eof()
        self.pid = 12345

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr

    async def wait(self):
        return self.returncode


@pytest.mark.asyncio
async def test_async_run_happy_path(tmp_path, monkeypatch):
    mod = import_codex_with_env(tmp_path)
    ws = await mod.create_workspace("asyncok")
    ws_id = ws["workspace_id"]
    lines = [json.dumps({"type": "turn.started"}), json.dumps({"type": "turn.completed"})]

    async def fake_create_subprocess_exec(*args, **kwargs):
        return FakeProc(stdout_lines=lines, stderr_lines=[], returncode=0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    start = await mod.start_codex_run(ws_id, "do it", json_events=True)
    assert start["status"] == "queued"
    run_id = start["run_id"]
    # Poll for completion
    for _ in range(50):
        status = await mod.get_codex_run(run_id)
        if status["run"]["status"] in ("completed", "failed"):
            break
        await asyncio.sleep(0.02)
    assert status["run"]["status"] == "completed"
    assert status["run"]["task_ok"] is True
    # events file should exist
    art = Path(status["run"]["artifacts"]["events_path"])  # type: ignore
    assert art.exists()

