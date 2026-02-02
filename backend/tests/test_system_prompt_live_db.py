import sys
from datetime import datetime, timezone


def test_print_system_prompt_from_live_db(capsys):
    """Print the actual system prompt and context using the configured MongoDB.

    - Does not assert on DB contents (so it won't fail CI environments).
    - Always prints the composed system prompt and formatted user context.
    """
    # Try to get live collections
    try:
        from db.mongodb import get_conversations_collection
        conv_col = get_conversations_collection()
    except Exception as e:
        sys.__stdout__.write("\n[SKIP] MongoDB not available: %s\n" % (str(e)))
        # Still pass the test to avoid CI failures
        assert True
        return

    # Build a minimal chat flow
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

    cp = ChatProcessor(request=None, payload=payload)

    # Initialize conversation and inject system prompt
    asyncio.get_event_loop().run_until_complete(cp._initialize_conversation())
    asyncio.get_event_loop().run_until_complete(cp._inject_profile_system_prompt())

    # Compute user context as the API would
    import services.context_service as ctx
    user_ctx = asyncio.get_event_loop().run_until_complete(ctx.get_user_context("default"))
    formatted_ctx = ctx.format_context_for_system_prompt(user_ctx)

    # Get assistant persona alone for clarity
    from services.profile_service import get_system_prompt_for_user
    persona = asyncio.get_event_loop().run_until_complete(get_system_prompt_for_user("default"))

    # Extract the final injected system message
    system_msg = cp.llm_history[0] if cp.llm_history and cp.llm_history[0].get("role") == "system" else {"content": "<none>"}
    content = system_msg.get("content", "<none>")

    # Print out all parts and bypass capture so they appear in terminal
    with capsys.disabled():
        print("\n===== ASSISTANT PERSONA (AI Profile) =====\n" + (persona or "<empty>"))
        print("\n===== FORMATTED USER CONTEXT (User Profile + Pins) =====\n" + (formatted_ctx or "<empty>"))
        print("\n===== COMBINED SYSTEM PROMPT INJECTED =====\n" + (content or "<empty>"))

    assert True
