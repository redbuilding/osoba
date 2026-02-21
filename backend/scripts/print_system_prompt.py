import os
import sys
import asyncio
from datetime import datetime, timezone


# Ensure the backend package is importable when running as a script
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv, find_dotenv
    _dotenv_path = find_dotenv(usecwd=True, raise_error_if_not_found=False)
    if _dotenv_path:
        load_dotenv(_dotenv_path)
    else:
        load_dotenv()
except Exception:
    pass


async def main():
    # Build a minimal chat to force injection
    try:
        from services.chat_service import ChatProcessor
        from core.models import ChatPayload
        from services.profile_service import get_system_prompt_for_user
        import services.context_service as ctx
    except Exception as e:
        print(f"Failed to import backend modules: {e}")
        return

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

    try:
        cp = ChatProcessor(request=None, payload=payload)
        await cp._initialize_conversation()
        await cp._inject_profile_system_prompt()
    except Exception as e:
        print(f"Failed to build or inject system prompt (DB available?): {e}")
        return

    # Persona and context
    persona = await get_system_prompt_for_user("default")
    user_ctx = await ctx.get_user_context("default")
    formatted_ctx = ctx.format_context_for_system_prompt(user_ctx)

    system_msg = cp.llm_history[0] if cp.llm_history and cp.llm_history[0].get("role") == "system" else {"content": "<none>"}
    content = system_msg.get("content", "<none>")

    print("\n===== ASSISTANT PERSONA (AI Profile) =====\n" + (persona or "<empty>"))
    print("\n===== FORMATTED USER CONTEXT (User Profile + Pins) =====\n" + (formatted_ctx or "<empty>"))
    print("\n===== COMBINED SYSTEM PROMPT INJECTED =====\n" + (content or "<empty>"))


if __name__ == "__main__":
    asyncio.run(main())
