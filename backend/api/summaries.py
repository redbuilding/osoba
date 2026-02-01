from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from core.config import get_logger
from db import crud
from db.settings_crud import get_user_settings, save_user_settings
from services.provider_service import chat_with_provider

logger = get_logger("summaries_api")
router = APIRouter()

class SummarySettingsPayload(BaseModel):
    model_name: str

class GenerateSummaryPayload(BaseModel):
    conversation_id: str

@router.get("/api/summaries/settings")
async def get_summary_settings(user_id: str = "default") -> Dict[str, Any]:
    try:
        settings = get_user_settings(user_id) or {}
        model_name = settings.get("chat_summaries", {}).get("model_name")
        return {"model_name": model_name or ""}
    except Exception as e:
        logger.error(f"Error getting summary settings: {e}")
        raise HTTPException(status_code=500, detail="Error getting summary settings")

@router.post("/api/summaries/settings")
async def save_summary_settings(payload: SummarySettingsPayload, user_id: str = "default"):
    try:
        settings = get_user_settings(user_id) or {}
        settings.setdefault("chat_summaries", {})
        settings["chat_summaries"]["model_name"] = payload.model_name
        ok = save_user_settings(user_id, settings)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to save settings")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving summary settings: {e}")
        raise HTTPException(status_code=500, detail="Error saving summary settings")

def _strip_html(text: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _limit_words(text: str, max_words: int = 1000) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])

@router.post("/api/summaries/generate")
async def generate_summary(payload: GenerateSummaryPayload, user_id: str = "default"):
    """Generate an AI summary for a conversation and save it. Limits source to ~1000 words, and output to 750 chars."""
    try:
        messages = crud.get_messages_by_conv_id(payload.conversation_id)
        if messages is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Build source text from most recent to older, stopping at ~1000 words
        combined = []
        total_words = 0
        for msg in reversed(messages):  # start from newest
            role = msg.role
            content = _strip_html(msg.content or "")
            if not content:
                continue
            words = content.split()
            if total_words + len(words) > 1000:
                remaining = max(0, 1000 - total_words)
                content = " ".join(words[:remaining])
                combined.append(f"{role}: {content}")
                total_words = 1000
                break
            combined.append(f"{role}: {content}")
            total_words += len(words)

        source_text = "\n".join(combined)

        # Fetch configured model
        settings = get_user_settings(user_id) or {}
        model_name = settings.get("chat_summaries", {}).get("model_name")
        if not model_name:
            # Fallback to DEFAULT_MODEL through provider prefixes (ollama/<model> or openai/gpt-*)
            from core.config import DEFAULT_MODEL
            model_name = DEFAULT_MODEL

        system_prompt = (
            "You create concise, information-dense chat summaries for future task context. "
            "Summarize in at most 750 characters (about 150 words). Capture: goal, key steps (3–5), decisions/outcomes, "
            "tools/data/APIs used, important links, and next steps. Use a single paragraph without headings, bullets, or markdown."
        )
        user_prompt = (
            "Summarize the following conversation for reuse as context. Be specific and include concrete steps, decisions, tools, and any link if present.\n\n"
            f"Conversation (most recent first):\n{source_text}"
        )
        llm_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await chat_with_provider(llm_messages, model_name, user_id=user_id)
        if not response:
            raise HTTPException(status_code=502, detail="LLM did not return a response")

        summary = response.strip()
        if len(summary) > 750:
            summary = summary[:750].rstrip()

        ok = crud.update_conversation_summary(payload.conversation_id, summary)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to save summary")

        return {"success": True, "summary": summary}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail="Error generating summary")

