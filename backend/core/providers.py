import os
from typing import Dict, List, Optional, Any

# Provider configuration constants
PROVIDER_CONFIGS = {
    'ollama': {
        'name': 'Ollama',
        'api_key_env': None,  # No API key needed for local Ollama
        'api_base_env': 'OLLAMA_API_BASE',
        'default_api_base': 'http://localhost:11434',
        'model_prefix': 'ollama/',
        'default_models': ['llama3.1', 'mistral', 'codellama'],
        'supports_streaming': True,
        'requires_max_tokens': False,
        'health_check_model': 'llama3.1'
    },
    'openai': {
        'name': 'OpenAI',
        'api_key_env': 'OPENAI_API_KEY',
        'api_base_env': 'OPENAI_API_BASE',
        'default_api_base': None,  # Uses LiteLLM default
        'model_prefix': 'openai/',
        'default_models': ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo'],
        'supports_streaming': True,
        'requires_max_tokens': False,
        'health_check_model': 'gpt-3.5-turbo'
    },
    'anthropic': {
        'name': 'Anthropic',
        'api_key_env': 'ANTHROPIC_API_KEY',
        'api_base_env': None,
        'default_api_base': None,
        'model_prefix': 'anthropic/',
        'default_models': ['claude-3-sonnet-20240229', 'claude-3-haiku-20240307', 'claude-3-opus-20240229'],
        'supports_streaming': True,
        'requires_max_tokens': True,  # Anthropic requires max_tokens
        'default_max_tokens': 4096,
        'health_check_model': 'claude-3-haiku-20240307'
    },
    'google': {
        'name': 'Google',
        'api_key_env': 'GEMINI_API_KEY',
        'api_base_env': None,
        'default_api_base': None,
        'model_prefix': 'gemini/',
        'default_models': ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro'],
        'supports_streaming': True,
        'requires_max_tokens': False,
        'health_check_model': 'gemini-1.5-flash'
    },
    'openrouter': {
        'name': 'OpenRouter',
        'api_key_env': 'OPENROUTER_API_KEY',
        'api_base_env': None,
        'default_api_base': None,
        'model_prefix': 'openrouter/',
        'default_models': ['openrouter/anthropic/claude-3-sonnet', 'openrouter/openai/gpt-4', 'openrouter/meta-llama/llama-3.1-8b-instruct'],
        'supports_streaming': True,
        'requires_max_tokens': False,
        'health_check_model': 'openrouter/meta-llama/llama-3.1-8b-instruct'
    },
    'groq': {
        'name': 'Groq',
        'api_key_env': 'GROQ_API_KEY',
        'api_base_env': None,
        'default_api_base': None,
        'model_prefix': 'groq/',
        'default_models': ['groq/llama3-8b-8192', 'groq/mixtral-8x7b-32768', 'groq/gemma-7b-it'],
        'supports_streaming': True,
        'requires_max_tokens': False,
        'health_check_model': 'groq/llama3-8b-8192'
    },
    'sambanova': {
        'name': 'SambaNova',
        'api_key_env': 'SAMBANOVA_API_KEY',
        'api_base_env': None,
        'default_api_base': None,
        'model_prefix': 'sambanova/',
        'default_models': ['sambanova/Meta-Llama-3.1-8B-Instruct', 'sambanova/Meta-Llama-3.1-70B-Instruct'],
        'supports_streaming': True,
        'requires_max_tokens': False,
        'health_check_model': 'sambanova/Meta-Llama-3.1-8B-Instruct'
    }
}

def get_provider_config(provider_id: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific provider."""
    return PROVIDER_CONFIGS.get(provider_id)

def get_available_providers() -> List[str]:
    """Get list of all available provider IDs."""
    return list(PROVIDER_CONFIGS.keys())

def get_provider_display_name(provider_id: str) -> str:
    """Get display name for a provider."""
    config = get_provider_config(provider_id)
    return config['name'] if config else provider_id.title()

def is_provider_configured(provider_id: str) -> bool:
    """Check if a provider is configured (has API key if required)."""
    config = get_provider_config(provider_id)
    if not config:
        return False
    
    # Ollama doesn't need API key
    if provider_id == 'ollama':
        return True
    
    # Check if API key is available
    api_key_env = config.get('api_key_env')
    if api_key_env:
        return bool(os.getenv(api_key_env))
    
    return False

def get_model_with_prefix(provider_id: str, model_name: str) -> str:
    """Get model name with proper provider prefix."""
    config = get_provider_config(provider_id)
    if not config:
        return model_name
    
    prefix = config.get('model_prefix', '')
    
    # If model already has prefix, return as-is
    if model_name.startswith(prefix):
        return model_name
    
    # For OpenRouter, models already include the full path
    if provider_id == 'openrouter' and '/' in model_name:
        return f"{prefix}{model_name}"
    
    # For other providers, add prefix
    return f"{prefix}{model_name}"

def extract_provider_from_model(model_name: str) -> tuple[str, str]:
    """Extract provider and clean model name from a full model string."""
    for provider_id, config in PROVIDER_CONFIGS.items():
        prefix = config.get('model_prefix', '')
        if model_name.startswith(prefix):
            clean_model = model_name[len(prefix):]
            return provider_id, clean_model
    
    # Default to ollama if no prefix found
    return 'ollama', model_name
