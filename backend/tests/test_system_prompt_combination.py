from fastapi import FastAPI
from fastapi.testclient import TestClient
import types


def test_system_prompt_includes_ai_and_user_context(monkeypatch):
    # Patch chat_service dependencies
    import services.chat_service as chat
    import services.context_service as ctx

    # Avoid real Mongo client in ChatProcessor __init__
    monkeypatch.setattr(chat, "get_conversations_collection", lambda: types.SimpleNamespace())

    # Return a fixed assistant persona from AI Profile
    async def fake_get_system_prompt(user_id: str = "default"):
        return "You are Nova, an AI assistant with a friendly style."

    monkeypatch.setattr(chat, "get_system_prompt_for_user", fake_get_system_prompt)

    # Provide a concrete user context
    async def fake_get_user_context(user_id: str = "default"):
        return {
            "profile_context": "User role: Product Manager | Expertise: SQL, Roadmaps | Preferred communication: concise",
            "conversation_context": "Roadmap planning chat summary",
            "total_chars": 123,
        }

    monkeypatch.setattr(ctx, "get_user_context", fake_get_user_context)

    # Provide a user profile to avoid DB fetch
    class FakeUserProfilesCrud:
        @staticmethod
        def get_user_profile(user_id: str = "default"):
            return {
                "name": "Alex",
                "role": "Product Manager",
                "communication_style": "concise",
                "expertise_areas": ["SQL", "Roadmaps"],
                "current_projects": "Onboarding revamp",
            }

    monkeypatch.setattr(chat, "user_profiles_crud", FakeUserProfilesCrud)

    # Build a minimal ChatProcessor instance
    from core.models import ChatPayload

    payload = ChatPayload(
        user_message="Hello",
        chat_history=[],
        use_search=False,
        use_database=False,
        use_hubspot=False,
        use_youtube=False,
        use_python=False,
        conversation_id=None,
    )

    cp = chat.ChatProcessor(request=None, payload=payload)
    cp.llm_history = []  # Ensure no pre-existing system message

    # Invoke the injection method directly
    import asyncio
    asyncio.get_event_loop().run_until_complete(cp._inject_profile_system_prompt())

    assert len(cp.llm_history) >= 1
    system_msg = cp.llm_history[0]
    assert system_msg["role"] == "system"
    content = system_msg["content"]

    # Assert both assistant persona and user context appear with sections
    assert "=== Assistant Persona ===" in content
    assert "You are Nova, an AI assistant" in content
    assert "=== Human User ===" in content
    assert "Product Manager" in content
    assert "=== Conversation Context ===" in content
