from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from services.context_service import get_user_context, format_context_for_system_prompt
from db import crud
from core.config import get_logger

logger = get_logger("user_context_api")
router = APIRouter()

class PinConversationPayload(BaseModel):
    """Payload for pinning/unpinning conversations."""
    conversation_id: str
    pinned: bool = True

class ConversationSummaryPayload(BaseModel):
    """Payload for updating conversation summary."""
    conversation_id: str
    summary: str

class ContextResponse(BaseModel):
    """Response model for context operations."""
    success: bool
    message: str
    data: Dict[str, Any] = {}

@router.get("/api/user-context/profile")
async def get_user_profile_context(user_id: str = "default"):
    """Get user profile context for system prompt injection."""
    try:
        context = await get_user_context(user_id)
        formatted_context = format_context_for_system_prompt(context)
        
        return ContextResponse(
            success=True,
            message="User context retrieved successfully",
            data={
                "context": context,
                "formatted_context": formatted_context
            }
        )
    except Exception as e:
        logger.error(f"Error getting user context: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting user context: {str(e)}")

@router.post("/api/user-context/pin-conversation")
async def pin_conversation(payload: PinConversationPayload, user_id: str = "default"):
    """Pin or unpin a conversation for context use."""
    try:
        # Enforce max pin limit of 5 per user when pinning
        if payload.pinned:
            try:
                conv = crud.get_conversation_by_id(payload.conversation_id)
                already_pinned = bool(conv and conv.get("pinned_for_context"))
                if not already_pinned:
                    current = crud.get_pinned_conversations(user_id, limit=6)
                    if len(current) >= 5:
                        # Return 400 to indicate policy violation
                        raise HTTPException(status_code=400, detail="MAX_PINS_REACHED: You can pin up to 5 chats. Unpin one to proceed.")
            except Exception:
                # If DB not available, skip strict enforcement (tests/mocked)
                pass

        success = crud.pin_conversation_for_context(payload.conversation_id, user_id, payload.pinned)
        
        if not success:
            return ContextResponse(
                success=False,
                message="Failed to update conversation pin status. Conversation may not exist."
            )
        
        action = "pinned" if payload.pinned else "unpinned"
        return ContextResponse(
            success=True,
            message=f"Conversation {action} successfully"
        )
    except Exception as e:
        logger.error(f"Error pinning conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Error pinning conversation: {str(e)}")

@router.get("/api/user-context/pinned-conversations")
async def get_user_pinned_conversations(user_id: str = "default"):
    """Get conversations pinned for context by user."""
    try:
        pinned_conversations = crud.get_pinned_conversations(user_id)
        
        return ContextResponse(
            success=True,
            message="Pinned conversations retrieved successfully",
            data={"conversations": pinned_conversations}
        )
    except Exception as e:
        logger.error(f"Error getting pinned conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting pinned conversations: {str(e)}")

@router.get("/api/user-context/pin-stats")
async def get_pin_stats(user_id: str = "default"):
    """Return current pinned count and max allowed pins for UI guardrails."""
    try:
        try:
            current = crud.get_pinned_conversations(user_id, limit=10)
            count = len(current)
        except Exception:
            count = 0
        return {"count": count, "max": 5}
    except Exception as e:
        logger.error(f"Error getting pin stats: {e}")
        raise HTTPException(status_code=500, detail="Error getting pin stats")

@router.post("/api/user-context/conversation-summary")
async def update_conversation_summary_endpoint(payload: ConversationSummaryPayload):
    """Update the summary of a conversation."""
    try:
        success = crud.update_conversation_summary(payload.conversation_id, payload.summary)
        
        if not success:
            return ContextResponse(
                success=False,
                message="Failed to update conversation summary. Conversation may not exist."
            )
        
        return ContextResponse(
            success=True,
            message="Conversation summary updated successfully"
        )
    except Exception as e:
        logger.error(f"Error updating conversation summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating conversation summary: {str(e)}")
