import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def make_app():
    from backend.api import artifacts as artifacts_api
    app = FastAPI()
    app.include_router(artifacts_api.router)
    return app


def _set_artifacts_root(tmpdir: Path):
    # Point the artifact service to a temp root for isolation
    tmpdir.mkdir(parents=True, exist_ok=True)
    # Patch both import paths to avoid duplicate module instances
    from backend.services import artifact_service as art_pkg
    art_pkg.artifact_service.root = tmpdir.resolve()
    from backend.api import artifacts as artifacts_api
    artifacts_api.artifact_service.root = tmpdir.resolve()


def test_capabilities_endpoint():
    app = make_app()
    client = TestClient(app)
    r = client.get("/api/artifacts/capabilities")
    assert r.status_code == 200
    data = r.json()
    # Keys always present; booleans depend on optional deps
    assert set(data.keys()) == {"html", "docx", "pdf"}
    assert isinstance(data["html"], bool)
    assert isinstance(data["docx"], bool)
    assert isinstance(data["pdf"], bool)


def test_message_markdown_save_and_versioning(tmp_path):
    app = make_app()
    client = TestClient(app)
    _set_artifacts_root(tmp_path)

    payload = {
        "source_type": "message",
        "content": "Hello world\n\nThis is a test.",
        "format": "md",
        "path_template": "artifacts/{date}/messages/{title}.md",
        "title": "Test Message",
        "profile": "TestProfile",
    }
    r1 = client.post("/api/artifacts", json=payload)
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    p1 = Path(d1["path"])  # absolute path
    assert p1.exists() and p1.read_text().startswith("Hello world")
    assert d1["format"] == "md"
    assert d1["relative_path"].endswith(".md")

    # Save again with same payload should version the filename (…-v2.md)
    r2 = client.post("/api/artifacts", json=payload)
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    p2 = Path(d2["path"]).resolve()
    assert p2.exists()
    assert p2 != p1
    # Should be versioned with -vN.md where N>=2
    assert p2.suffix == ".md"
    assert "-v" in p2.stem


def test_message_md_forces_extension(tmp_path):
    app = make_app()
    client = TestClient(app)
    _set_artifacts_root(tmp_path)

    # Provide a .txt suffix but request md format; must end with .md
    payload = {
        "source_type": "message",
        "content": "Content",
        "format": "md",
        "path_template": "artifacts/custom/path/report.txt",
        "title": "My Title",
    }
    r = client.post("/api/artifacts", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["relative_path"].endswith(".md")
    assert Path(data["path"]).suffix == ".md"


def test_task_run_requires_completed_and_collates(tmp_path, monkeypatch):
    app = make_app()
    client = TestClient(app)
    _set_artifacts_root(tmp_path)

    # Patch get_task to simulate running then completed
    from backend.api import artifacts as artifacts_api

    running_doc = {"_id": "t1", "status": "RUNNING", "title": "Run", "model_name": "m", "profile_id": "p"}
    done_doc = {"_id": "t1", "status": "COMPLETED", "title": "Done", "model_name": "m", "profile_id": "p"}

    # First call returns running to assert 409
    state = {"count": 0}

    def fake_get_task(task_id):
        state["count"] += 1
        return running_doc if state["count"] == 1 else done_doc

    monkeypatch.setattr(artifacts_api, "get_task", fake_get_task)

    # Collation returns deterministic markdown
    monkeypatch.setattr(artifacts_api, "build_markdown", lambda tid, opts=None: "# Collated\nBody\n")

    # First attempt should 409 because task is RUNNING
    r1 = client.post(
        "/api/artifacts",
        json={
            "source_type": "task_run",
            "task_id": "t1",
            "format": "md",
            "path_template": "artifacts/{date}/tasks/{task_slug}/{run_id}-{title}.md",
        },
    )
    assert r1.status_code == 409

    # Second attempt sees completed doc and should collate and save
    r2 = client.post(
        "/api/artifacts",
        json={
            "source_type": "task_run",
            "task_id": "t1",
            "format": "md",
            "path_template": "artifacts/{date}/tasks/{task_slug}/{run_id}-{title}.md",
        },
    )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    p = Path(data["path"]).resolve()
    assert p.exists()
    assert p.read_text().startswith("# Collated")


def test_sanitize_relpath_and_write_confines_to_root(tmp_path):
    # Directly test service write with traversal sequences in rel path
    from backend.services.artifact_service import artifact_service
    artifact_service.root = tmp_path.resolve()

    abspath, size, checksum = artifact_service.write_text("../../outside/evil.md", "x")
    assert abspath.resolve().parent.parent == tmp_path.resolve()
    assert abspath.name == "evil.md"
    assert abspath.exists()
