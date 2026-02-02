from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.user_profile import router as user_profile_router
from api.user_context import router as user_context_router


def test_user_profile_crud_and_context(monkeypatch):
    app = FastAPI()
    app.include_router(user_profile_router)
    app.include_router(user_context_router)
    client = TestClient(app)

    # In-memory store
    store = {"profile": None}

    # Patch services used by user_profile API
    import api.user_profile as up_api

    async def fake_get_service(user_id: str = "default"):
        return store["profile"]

    async def fake_upsert_service(payload, user_id: str = "default"):
        data = payload.dict(exclude_unset=True)
        # Apply simple defaults and limiters similar to model
        profile = {
            "name": data.get("name", ""),
            "role": data.get("role"),
            "communication_style": data.get("communication_style", "professional"),
            "expertise_areas": (data.get("expertise_areas") or [])[:5],
            "current_projects": data.get("current_projects"),
            "preferred_tools": (data.get("preferred_tools") or [])[:10],
            "user_id": "default",
        }
        store["profile"] = profile
        return profile

    async def fake_delete_service(user_id: str = "default"):
        had = store["profile"] is not None
        store["profile"] = None
        return had

    monkeypatch.setattr(up_api, "get_user_profile_service", fake_get_service)
    monkeypatch.setattr(up_api, "upsert_user_profile_service", fake_upsert_service)
    monkeypatch.setattr(up_api, "delete_user_profile_service", fake_delete_service)

    # Also patch context service's CRUD to read from our store
    import services.context_service as ctx

    class FakeUserProfilesCrud:
        @staticmethod
        def get_user_profile(user_id: str = "default"):
            return store["profile"]

    monkeypatch.setattr(ctx, "user_profiles_crud", FakeUserProfilesCrud)

    # 1) Initially empty
    r = client.get("/api/user-profile")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["profile"] is None

    # 2) Save profile
    payload = {
        "name": "Alex",
        "role": "Software Developer",
        "communication_style": "friendly",
        "expertise_areas": ["JavaScript", "Machine Learning"],
        "current_projects": "Building a chat app",
        "preferred_tools": ["Web Search", "Database"],
    }
    r = client.put("/api/user-profile", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["profile"]["name"] == "Alex"
    assert data["profile"]["role"] == "Software Developer"

    # 3) Fetch and verify persistence
    r = client.get("/api/user-profile")
    assert r.status_code == 200
    data = r.json()
    assert data["profile"]["communication_style"] == "friendly"
    assert data["profile"]["expertise_areas"] == ["JavaScript", "Machine Learning"]

    # 4) Verify context endpoint uses profile info
    r = client.get("/api/user-context/profile")
    assert r.status_code == 200
    ctx_data = r.json()
    assert ctx_data["success"] is True
    formatted = ctx_data["data"]["formatted_context"]
    # Should reflect role and expertise in the formatted profile context
    assert "User role: Software Developer" in formatted or "User role: Software Developer" in ctx_data["data"]["context"].get("profile_context", "")
    assert "Expertise:" in formatted or "Expertise:" in ctx_data["data"]["context"].get("profile_context", "")

    # 5) Delete profile
    r = client.delete("/api/user-profile")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True

    # 6) Now empty again
    r = client.get("/api/user-profile")
    assert r.status_code == 200
    data = r.json()
    assert data["profile"] is None

