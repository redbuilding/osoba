from typing import Dict, List, Optional, Any
from db.profiles_crud import (
    get_user_profiles, get_profile_by_id, get_active_profile,
    create_profile, update_profile, delete_profile, set_active_profile
)
from core.profile_models import AIProfile, ProfileCreatePayload, ProfileUpdatePayload
from core.config import get_logger

logger = get_logger("profile_service")

def generate_system_prompt(profile_data: Dict[str, Any]) -> str:
    """Generate a system prompt based on profile data."""
    if not profile_data:
        return ""
    
    name = profile_data.get("name")
    communication_style = profile_data.get("communication_style")
    expertise_areas = profile_data.get("expertise_areas", [])
    
    # If no name or style, return empty (no profile data)
    if not name and not communication_style:
        return ""
    
    # Use defaults if missing
    name = name or "Assistant"
    communication_style = communication_style or "professional"
    
    prompt_parts = [
        f"You are {name}, an AI assistant with a {communication_style} communication style."
    ]
    
    if expertise_areas:
        expertise_str = ", ".join(expertise_areas)
        prompt_parts.append(f"Your areas of expertise include: {expertise_str}.")
    
    # Add style-specific instructions
    style_instructions = {
        "professional": "Maintain a formal, business-appropriate tone. Be concise and direct.",
        "friendly": "Use a warm, approachable tone. Be conversational and encouraging.",
        "casual": "Keep things relaxed and informal. Use everyday language and be personable.",
        "technical": "Focus on precision and accuracy. Use technical terminology when appropriate.",
        "creative": "Be imaginative and expressive. Think outside the box and offer innovative solutions.",
        "supportive": "Be empathetic and understanding. Provide encouragement and positive reinforcement."
    }
    
    if communication_style in style_instructions:
        prompt_parts.append(style_instructions[communication_style])
    
    return " ".join(prompt_parts)

async def get_profiles_for_user(user_id: str = "default") -> List[Dict[str, Any]]:
    """Get all profiles for a user."""
    try:
        profiles = get_user_profiles(user_id)
        return profiles
    except Exception as e:
        logger.error(f"Error getting profiles for user {user_id}: {e}")
        return []

async def get_profile_by_id_service(profile_id: str, user_id: str = "default") -> Optional[Dict[str, Any]]:
    """Get a specific profile by ID."""
    try:
        return get_profile_by_id(profile_id, user_id)
    except Exception as e:
        logger.error(f"Error getting profile {profile_id}: {e}")
        return None

async def get_active_profile_service(user_id: str = "default") -> Optional[Dict[str, Any]]:
    """Get the active profile for a user."""
    try:
        return get_active_profile(user_id)
    except Exception as e:
        logger.error(f"Error getting active profile for user {user_id}: {e}")
        return None

async def create_profile_service(payload: ProfileCreatePayload, user_id: str = "default") -> Optional[str]:
    """Create a new profile."""
    try:
        profile_data = payload.dict()
        return create_profile(profile_data, user_id)
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        return None

async def update_profile_service(profile_id: str, payload: ProfileUpdatePayload, user_id: str = "default") -> bool:
    """Update an existing profile."""
    try:
        update_data = payload.dict(exclude_unset=True)
        return update_profile(profile_id, update_data, user_id)
    except Exception as e:
        logger.error(f"Error updating profile {profile_id}: {e}")
        return False

async def delete_profile_service(profile_id: str, user_id: str = "default") -> bool:
    """Delete a profile."""
    try:
        return delete_profile(profile_id, user_id)
    except Exception as e:
        logger.error(f"Error deleting profile {profile_id}: {e}")
        return False

async def set_active_profile_service(profile_id: Optional[str], user_id: str = "default") -> bool:
    """Set the active profile for a user."""
    try:
        return set_active_profile(profile_id, user_id)
    except Exception as e:
        logger.error(f"Error setting active profile: {e}")
        return False

async def get_system_prompt_for_user(user_id: str = "default") -> str:
    """Get the system prompt for the user's active profile."""
    try:
        active_profile = get_active_profile(user_id)
        if active_profile:
            return generate_system_prompt(active_profile)
        return ""
    except Exception as e:
        logger.error(f"Error getting system prompt for user {user_id}: {e}")
        return ""
