from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from db.crud import get_conversation_by_id, get_all_conversations
from db.profiles_crud import get_active_profile
from core.config import get_logger

logger = get_logger("context_service")

# Context size limits to prevent token overflow
MAX_PROFILE_CHARS = 200
MAX_CONVERSATION_CONTEXT_CHARS = 500
MAX_TOTAL_CONTEXT_CHARS = 800
MAX_PINNED_CONVERSATIONS = 5

async def get_user_context(user_id: str = "default") -> Dict[str, Any]:
    """Get comprehensive user context including profile and pinned conversations."""
    try:
        context = {
            "profile_context": "",
            "conversation_context": "",
            "total_chars": 0
        }
        
        # Get profile context
        profile_context = await get_profile_context(user_id)
        if profile_context:
            context["profile_context"] = profile_context[:MAX_PROFILE_CHARS]
        
        # Get conversation context
        conversation_context = await get_conversation_context(user_id)
        if conversation_context:
            context["conversation_context"] = conversation_context[:MAX_CONVERSATION_CONTEXT_CHARS]
        
        # Calculate total context size
        context["total_chars"] = len(context["profile_context"]) + len(context["conversation_context"])
        
        return context
    except Exception as e:
        logger.error(f"Error getting user context for {user_id}: {e}")
        return {"profile_context": "", "conversation_context": "", "total_chars": 0}

async def get_profile_context(user_id: str = "default") -> str:
    """Generate profile context string for system prompt injection."""
    try:
        profile = get_active_profile(user_id)
        if not profile:
            return ""
        
        context_parts = []
        
        # Add role information
        if profile.get("role"):
            context_parts.append(f"User role: {profile['role']}")
        
        # Add expertise areas
        expertise = profile.get("expertise_areas", [])
        if expertise:
            context_parts.append(f"Expertise: {', '.join(expertise)}")
        
        # Add current projects
        if profile.get("current_projects"):
            context_parts.append(f"Current projects: {profile['current_projects']}")
        
        # Add communication style
        if profile.get("communication_style"):
            context_parts.append(f"Preferred communication: {profile['communication_style']}")
        
        return " | ".join(context_parts)
    except Exception as e:
        logger.error(f"Error getting profile context for {user_id}: {e}")
        return ""

async def get_conversation_context(user_id: str = "default") -> str:
    """Get context from pinned conversations."""
    try:
        # Get pinned conversations for user
        pinned_conversations = get_pinned_conversations(user_id)
        if not pinned_conversations:
            return ""
        
        context_parts = []
        char_count = 0
        
        for conv in pinned_conversations[:MAX_PINNED_CONVERSATIONS]:
            if char_count >= MAX_CONVERSATION_CONTEXT_CHARS:
                break
                
            summary = conv.get("summary", "")
            title = conv.get("title", "Untitled")
            
            if summary:
                conv_context = f"{title}: {summary}"
                if char_count + len(conv_context) <= MAX_CONVERSATION_CONTEXT_CHARS:
                    context_parts.append(conv_context)
                    char_count += len(conv_context)
        
        return " | ".join(context_parts)
    except Exception as e:
        logger.error(f"Error getting conversation context for {user_id}: {e}")
        return ""

def get_pinned_conversations(user_id: str = "default") -> List[Dict[str, Any]]:
    """Get conversations pinned for context by user."""
    try:
        from db.crud import get_pinned_conversations as get_pinned_from_db
        return get_pinned_from_db(user_id, MAX_PINNED_CONVERSATIONS)
    except Exception as e:
        logger.error(f"Error getting pinned conversations for {user_id}: {e}")
        return []

def generate_conversation_summary(conversation_data: Dict[str, Any]) -> str:
    """Generate a brief summary of a conversation for context use."""
    try:
        messages = conversation_data.get("messages", [])
        if not messages:
            return ""
        
        # Simple summary generation - take key points from messages
        summary_parts = []
        for msg in messages[-5:]:  # Last 5 messages for context
            content = msg.get("content", "")
            if len(content) > 100:
                content = content[:100] + "..."
            if content and msg.get("role") == "user":
                summary_parts.append(content)
        
        return " | ".join(summary_parts)[:200]  # Limit summary length
    except Exception as e:
        logger.error(f"Error generating conversation summary: {e}")
        return ""

def format_context_for_system_prompt(context: Dict[str, Any]) -> str:
    """Format user context for injection into system prompt."""
    try:
        prompt_parts = []
        
        if context.get("profile_context"):
            prompt_parts.append(f"User Context: {context['profile_context']}")
        
        if context.get("conversation_context"):
            prompt_parts.append(f"Previous Conversations: {context['conversation_context']}")
        
        if prompt_parts:
            return "Context Information: " + " | ".join(prompt_parts)
        
        return ""
    except Exception as e:
        logger.error(f"Error formatting context for system prompt: {e}")
        return ""
