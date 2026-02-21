import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from bson import ObjectId
from cryptography.fernet import Fernet
from db.mongodb import get_settings_collection
from core.config import get_logger

logger = get_logger("settings_crud")

# Encryption key for API keys - should be set via environment variable
ENCRYPTION_KEY = os.getenv('SETTINGS_ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    # Generate a key for development - in production this should be set externally
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    logger.error(
        "SETTINGS_ENCRYPTION_KEY is not set! API keys will be lost on restart. "
        "Generate a stable key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
        "Then add SETTINGS_ENCRYPTION_KEY=<key> to your backend/.env file."
    )

fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for secure storage."""
    if not api_key:
        return ""
    return fernet.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key from storage.
    Backward compatible: if decryption fails, treat as plaintext to avoid breaking existing records.
    """
    if not encrypted_key:
        return ""
    try:
        return fernet.decrypt(encrypted_key.encode()).decode()
    except Exception as e:
        # Likely encrypted with a different SETTINGS_ENCRYPTION_KEY. Do not return the ciphertext
        # as a usable API key; treat as missing so the UI shows provider unconfigured and the
        # user can re-enter the key. Avoid logging the key itself.
        logger.warning("Stored API key can't be decrypted with current SETTINGS_ENCRYPTION_KEY; treating as missing.")
        return ""

def get_user_settings(user_id: str = "default") -> Optional[Dict[str, Any]]:
    """Get user settings including provider configurations."""
    try:
        collection = get_settings_collection()
        settings = collection.find_one({"user_id": user_id})
        
        if settings:
            # Decrypt API keys for use
            if "providers" in settings:
                for provider_id, provider_config in settings["providers"].items():
                    if "api_key" in provider_config and provider_config["api_key"]:
                        provider_config["api_key"] = decrypt_api_key(provider_config["api_key"])
        
        return settings
    except Exception as e:
        logger.error(f"Error getting user settings: {e}")
        return None

def save_user_settings(user_id: str = "default", settings: Dict[str, Any] = None) -> bool:
    """Save user settings with encrypted API keys."""
    try:
        if not settings:
            settings = {}
        
        # Encrypt API keys before storage
        settings_to_save = settings.copy()
        if "providers" in settings_to_save:
            for provider_id, provider_config in settings_to_save["providers"].items():
                if "api_key" in provider_config and provider_config["api_key"]:
                    provider_config["api_key"] = encrypt_api_key(provider_config["api_key"])
        
        settings_to_save.update({
            "user_id": user_id,
            "updated_at": datetime.now(timezone.utc)
        })
        
        collection = get_settings_collection()
        result = collection.replace_one(
            {"user_id": user_id},
            settings_to_save,
            upsert=True
        )
        
        return result.acknowledged
    except Exception as e:
        logger.error(f"Error saving user settings: {e}")
        return False

def update_provider_api_key(provider_id: str, api_key: str, user_id: str = "default") -> bool:
    """Update API key for a specific provider."""
    try:
        settings = get_user_settings(user_id) or {}
        
        if "providers" not in settings:
            settings["providers"] = {}
        
        if provider_id not in settings["providers"]:
            settings["providers"][provider_id] = {}
        
        settings["providers"][provider_id]["api_key"] = api_key
        settings["providers"][provider_id]["configured_at"] = datetime.now(timezone.utc).isoformat()
        
        return save_user_settings(user_id, settings)
    except Exception as e:
        logger.error(f"Error updating provider API key: {e}")
        return False

def get_provider_api_key(provider_id: str, user_id: str = "default") -> Optional[str]:
    """Get decrypted API key for a specific provider."""
    try:
        settings = get_user_settings(user_id)
        if not settings or "providers" not in settings:
            return None
        
        provider_config = settings["providers"].get(provider_id, {})
        return provider_config.get("api_key")
    except Exception as e:
        logger.error(f"Error getting provider API key: {e}")
        return None

def remove_provider_api_key(provider_id: str, user_id: str = "default") -> bool:
    """Remove API key for a specific provider."""
    try:
        settings = get_user_settings(user_id)
        if not settings or "providers" not in settings:
            return True  # Nothing to remove
        
        if provider_id in settings["providers"]:
            if "api_key" in settings["providers"][provider_id]:
                del settings["providers"][provider_id]["api_key"]
            
            # Remove empty provider config
            if not settings["providers"][provider_id]:
                del settings["providers"][provider_id]
        
        return save_user_settings(user_id, settings)
    except Exception as e:
        logger.error(f"Error removing provider API key: {e}")
        return False

def validate_provider_settings(provider_id: str, user_id: str = "default") -> Dict[str, Any]:
    """Validate provider settings and return status."""
    try:
        api_key = get_provider_api_key(provider_id, user_id)
        
        return {
            "provider_id": provider_id,
            "configured": bool(api_key),
            "has_api_key": bool(api_key),
            "validated_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error validating provider settings: {e}")
        return {
            "provider_id": provider_id,
            "configured": False,
            "has_api_key": False,
            "error": str(e)
        }
