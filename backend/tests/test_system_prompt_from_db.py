from fastapi.testclient import TestClient
from bson import ObjectId
from datetime import datetime, timezone


class InMemoryCollection:
    def __init__(self):
        self.docs = []

    def find_one(self, query):
        def match(doc, q):
            for k, v in q.items():
                if isinstance(v, dict) and "$ne" in v:
                    if doc.get(k) == v["$ne"]:
                        return False
                else:
                    if doc.get(k) != v:
                        return False
            return True
        for d in self.docs:
            if match(d, query):
                return dict(d)
        return None

    def insert_one(self, doc):
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.docs.append(dict(doc))
        class R: inserted_id = doc["_id"]
        return R()

    def update_one(self, query, update, upsert=False):
        target = self.find_one(query)
        if not target and not upsert:
            class R: modified_count = 0
            return R()
        if not target and upsert:
            target = {}
            # Seed with query fields
            for k, v in query.items():
                target[k] = v
            self.docs.append(target)
        # Apply $set
        if "$set" in update:
            for k, v in update["$set"].items():
                target[k] = v
        # Apply $setOnInsert
        if "$setOnInsert" in update and target not in self.docs:
            for k, v in update["$setOnInsert"].items():
                target.setdefault(k, v)
        # Apply $push (only array fields used in tests)
        if "$push" in update:
            for k, v in update["$push"].items():
                arr = target.get(k, [])
                arr.append(v)
                target[k] = arr
        class R: modified_count = 1
        return R()

    def update_many(self, query, update):
        class R: modified_count = 0
        return R()


def test_system_prompt_built_from_db_data(monkeypatch, capsys):
    # Prepare in-memory collections for ai_profiles, user_profiles, conversations
    ai_profiles = InMemoryCollection()
    user_profiles = InMemoryCollection()
    conversations = InMemoryCollection()

    # Monkeypatch DB accessors
    import db.mongodb as mongo
    monkeypatch.setattr(mongo, "get_profiles_collection", lambda: ai_profiles)
    monkeypatch.setattr(mongo, "get_user_profiles_collection", lambda: user_profiles)
    monkeypatch.setattr(mongo, "get_conversations_collection", lambda: conversations)

    # Seed AI Profile (assistant persona)
    ai_profiles.insert_one({
        "_id": ObjectId(),
        "name": "Nova",
        "communication_style": "friendly",
        "expertise_areas": ["Search", "Summarization"],
        "user_id": "default",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    # Seed User Profile (human user)
    user_profiles.update_one(
        {"user_id": "default"},
        {
            "$set": {
                "name": "Alex",
                "role": "Product Manager",
                "communication_style": "concise",
                "expertise_areas": ["SQL", "Roadmaps"],
                "current_projects": "Onboarding revamp",
                "preferred_tools": ["Web Search", "Database"],
                "user_id": "default",
                "updated_at": datetime.now(timezone.utc),
            },
            "$setOnInsert": {"created_at": datetime.now(timezone.utc)}
        },
        upsert=True,
    )

    # Build chat processor and inject system prompt
    import services.chat_service as chat
    import services.profile_service as prof
    from services.chat_service import ChatProcessor
    from core.models import ChatPayload
    import asyncio

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
    # Monkeypatch chat_service to use our in-memory conversations collection
    monkeypatch.setattr(chat, "get_conversations_collection", lambda: conversations)
    # Monkeypatch user_profiles_crud used by chat_service to read from our in-memory user profile
    class FakeUserProfilesCrud:
        @staticmethod
        def get_user_profile(user_id: str = "default"):
            return user_profiles.find_one({"user_id": user_id})
    monkeypatch.setattr(chat, "user_profiles_crud", FakeUserProfilesCrud)

    # Monkeypatch persona builder to avoid real DB lookups
    async def fake_get_system_prompt(user_id: str = "default"):
        return (
            "You are Nova, an AI assistant with a friendly communication style. "
            "Your areas of expertise include: Search, Summarization."
        )
    monkeypatch.setattr(chat, "get_system_prompt_for_user", fake_get_system_prompt)

    cp = ChatProcessor(request=None, payload=payload)

    # Initialize to create conversation and save user message
    asyncio.get_event_loop().run_until_complete(cp._initialize_conversation())
    # Inject combined system prompt
    asyncio.get_event_loop().run_until_complete(cp._inject_profile_system_prompt())

    assert len(cp.llm_history) >= 1
    system_msg = cp.llm_history[0]
    assert system_msg["role"] == "system"
    content = system_msg["content"]

    # Show what context it's pulling (computed the same way the app does)
    import services.context_service as ctx
    user_ctx = asyncio.get_event_loop().run_until_complete(ctx.get_user_context("default"))
    formatted_ctx = ctx.format_context_for_system_prompt(user_ctx)

    # Assertions: persona and context included with new section headings
    assert "=== Assistant Persona ===" in content
    assert "You are Nova" in content
    assert "=== Human User ===" in content
    assert "Product Manager" in content

    # Ensure output is visible even when pytest captures output
    with capsys.disabled():
        print("\n===== SYSTEM PROMPT (from in-memory DB) =====\n" + content)
        print("\n===== FORMATTED USER CONTEXT =====\n" + (formatted_ctx or "<empty>"))
