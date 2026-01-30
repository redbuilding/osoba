import asyncio
import json
import os
import sys
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure project root is on sys.path so `backend` package can be imported
TESTS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(TESTS_DIR, "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
for p in (PROJECT_ROOT, BACKEND_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)


# --- Planner tests ---
@pytest.mark.asyncio
async def test_planner_fallback(monkeypatch):
    from backend.services import task_planner as planner

    # Force chat_with_ollama to return malformed JSON
    async def fake_chat(messages, model_name, repeat_penalty=1.15):
        return "not-json"

    monkeypatch.setattr("backend.services.task_planner.chat_with_ollama", fake_chat)

    plan = await planner.plan_task("research something", model="llama-test", budget=None)
    assert plan.steps, "Planner should return at least one step"
    assert plan.steps[0].tool in planner.ALLOWED_TASK_TOOLS
    # Ensure LLM-only tool appears in allowed set
    assert "llm.generate" in planner.ALLOWED_TASK_TOOLS


# --- Progress bus tests ---
@pytest.mark.asyncio
async def test_progress_bus_pubsub():
    from backend.services.progress_bus import progress_bus

    task_id = "t1"
    events = []

    async def reader():
        agen = progress_bus.subscribe(task_id)
        for _ in range(2):
            chunk = await agen.__anext__()
            assert chunk.startswith("data: ")
            payload = json.loads(chunk[len("data: ") :].strip())
            events.append(payload)

    async def writer():
        await progress_bus.publish(task_id, {"hello": 1})
        await progress_bus.publish(task_id, {"world": 2})

    await asyncio.wait_for(asyncio.gather(reader(), writer()), timeout=2)
    assert events == [{"hello": 1}, {"world": 2}]


# --- Runner helper tests ---
def test_resolve_tool_mapping():
    from backend.services.task_runner import _resolve_tool
    from backend.core.config import (
        WEB_SEARCH_SERVICE_NAME,
        MYSQL_DB_SERVICE_NAME,
        YOUTUBE_SERVICE_NAME,
        PYTHON_SERVICE_NAME,
    )

    assert _resolve_tool("web_search") == (WEB_SEARCH_SERVICE_NAME, "web_search")
    assert _resolve_tool("execute_sql_query_tool") == (MYSQL_DB_SERVICE_NAME, "execute_sql_query_tool")
    assert _resolve_tool("get_youtube_transcript") == (YOUTUBE_SERVICE_NAME, "get_youtube_transcript")
    assert _resolve_tool("python.create_plot") == (PYTHON_SERVICE_NAME, "create_plot")


# --- API tests for tasks router with in-memory store ---
class MemoryTasks:
    def __init__(self):
        self.docs = {}

    def create_task(self, doc):
        _id = str(len(self.docs) + 1)
        doc = dict(doc)
        doc["_id"] = _id
        self.docs[_id] = doc
        return _id

    def get_task(self, tid):
        return dict(self.docs.get(tid)) if tid in self.docs else None

    def list_tasks(self):
        return [dict(v) for v in self.docs.values()]

    def update_task(self, tid, patch):
        if tid in self.docs:
            self.docs[tid].update(patch)


def make_app_with_memory_store(mem: MemoryTasks) -> FastAPI:
    from backend.api import tasks as tasks_api
    app = FastAPI()

    # Patch CRUD functions to use memory
    tasks_api.create_task = lambda payload: mem.create_task(payload)
    tasks_api.get_task = lambda tid: mem.get_task(tid)
    tasks_api.list_tasks = lambda: mem.list_tasks()
    tasks_api.update_task = lambda tid, patch: mem.update_task(tid, patch)

    app.include_router(tasks_api.router)
    return app


def test_tasks_api_create_list_detail(monkeypatch):
    mem = MemoryTasks()
    app = make_app_with_memory_store(mem)
    client = TestClient(app)

    # Create task
    r = client.post("/api/tasks", json={"goal": "do a thing", "dry_run": True})
    assert r.status_code == 200
    tid = r.json()["id"]
    assert mem.get_task(tid)

    # List tasks
    r = client.get("/api/tasks")
    assert r.status_code == 200
    items = r.json()
    assert any(t["id"] == tid for t in items)

    # Detail
    r = client.get(f"/api/tasks/{tid}")
    assert r.status_code == 200
    assert r.json()["id"] == tid


# --- Status API test (tasks.active) ---
@pytest.mark.asyncio
async def test_status_tasks_active(monkeypatch):
    from backend.api import status as status_api

    class FakeColl:
        def count_documents(self, q):
            return 3

    monkeypatch.setattr(status_api, "tasks_collection", FakeColl())
    data = await status_api.get_status()
    assert data["tasks"]["active"] == 3
