import json
import asyncio
from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_improve_instruction_endpoint_smoke(monkeypatch):
    # Mock provider chat to return the expected JSON structure
    async def fake_chat(messages, model_name, repeat_penalty=1.15):
        return json.dumps({
            "improved_text": "Cleaned instruction",
            "manifest": {"files": ["web/index.html", "web/styles.css"], "rules": ["keep ids"]},
            "step_plan": [{"title": "Do thing"}],
            "warnings": []
        })

    from backend.services import provider_service as ps
    monkeypatch.setattr(ps, "chat_with_provider", fake_chat)

    resp = client.post("/api/scheduled-tasks/improve-instruction", json={
        "draft_text": "Make a page and style it",
        "task_type": "scheduled",
        "model_name": None,
        "mode": "Clarify",
        "language": None,
        "context_hints": {"schedule": {"type": "daily"}}
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "improved_text" in data
    assert isinstance(data.get("manifest"), dict)
    assert isinstance(data.get("step_plan"), list)

