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
        'default_models': [
            'gpt-5.2',
            'gpt-5-nano',
            'gpt-5',
            'gpt-4.1',
            'gpt-oss-120b',
            'gpt-oss-20b',
        ],
        'supports_streaming': True,
        'requires_max_tokens': False,
        'health_check_model': 'gpt-5.2'
    },
    'anthropic': {
        'name': 'Anthropic',
        'api_key_env': 'ANTHROPIC_API_KEY',
        'api_base_env': None,
        'default_api_base': None,
        'model_prefix': 'anthropic/',
        'default_models': [
            'claude-opus-4-5',
            'claude-sonnet-4-5',
            'claude-haiku-4-5',
        ],
        'supports_streaming': True,
        'requires_max_tokens': True,  # Anthropic requires max_tokens
        'default_max_tokens': 4096,
        'health_check_model': 'claude-haiku-4-5'
    },
    'google': {
        'name': 'Google',
        'api_key_env': 'GEMINI_API_KEY',
        'api_base_env': None,
        'default_api_base': None,
        'model_prefix': 'gemini/',
        'default_models': [
            'gemini-3-pro-preview',
            'gemini-flash-latest',
            'gemini-flash-lite-latest',
        ],
        'supports_streaming': True,
        'requires_max_tokens': False,
        'health_check_model': 'gemini-flash-latest'
    },
    'openrouter': {
        'name': 'OpenRouter',
        'api_key_env': 'OPENROUTER_API_KEY',
        'api_base_env': None,
        'default_api_base': None,
        'model_prefix': 'openrouter/',
        'default_models': [
            'openrouter/moonshotai/kimi-k2.5',
            'openrouter/z-ai/glm-4.7',
            'openrouter/z-ai/glm-4.7-flash',
            'openrouter/qwen/qwen3-max',
            'openrouter/qwen/qwen3-coder-plus',
            'openrouter/qwen/qwen3-coder-flash',
            'openrouter/mistralai/mistral-large-2512',
            'openrouter/mistralai/codestral-2508',
            'openrouter/meta-llama/llama-4-maverick',
            'openrouter/meta-llama/llama-4-scout',
            'openrouter/meta-llama/llama-3.3-70b-instruct',
            'openrouter/meta-llama/llama-3.1-405b',
            'openrouter/x-ai/grok-4',
            'openrouter/x-ai/grok-4.1-fast',
        ],
        'supports_streaming': True,
        'requires_max_tokens': False,
        'health_check_model': 'openrouter/meta-llama/llama-3.3-70b-instruct'
    },
    'groq': {
        'name': 'Groq',
        'api_key_env': 'GROQ_API_KEY',
        'api_base_env': None,
        'default_api_base': None,
        'model_prefix': 'groq/',
        'default_models': [
            'groq/meta-llama/llama-guard-4-12b',
            'groq/llama-3.3-70b-versatile',
            'groq/llama-3.1-8b-instant',
            'groq/openai/gpt-oss-120b',
            'groq/openai/gpt-oss-20b',
        ],
        'supports_streaming': True,
        'requires_max_tokens': False,
        'health_check_model': 'groq/llama-3.1-8b-instant'
    },
    'sambanova': {
        'name': 'SambaNova',
        'api_key_env': 'SAMBANOVA_API_KEY',
        'api_base_env': None,
        'default_api_base': None,
        'model_prefix': 'sambanova/',
        'default_models': [
            'DeepSeek-R1-0528',
            'DeepSeek-V3-0324',
            'Meta-Llama-3.3-70B-Instruct',
            'Meta-Llama-3.1-8B-Instruct',
        ],
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
