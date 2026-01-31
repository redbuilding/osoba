# LiteLLM Multi-Provider Setup Guide

## Overview
LiteLLM provides a unified interface for multiple AI providers with consistent API key configuration, model naming conventions, and security best practices.

## Provider Configuration

### 1. OpenRouter
**API Key Configuration:**
```python
import os
os.environ["OPENROUTER_API_KEY"] = "your-api-key"
os.environ["OPENROUTER_API_BASE"] = "https://openrouter.ai/api/v1"  # Optional
os.environ["OR_SITE_URL"] = "your-site-url"  # Optional
os.environ["OR_APP_NAME"] = "your-app-name"  # Optional
```

**Model Naming Convention:**
```python
model = "openrouter/provider/model-name"
# Examples:
# "openrouter/openai/gpt-4"
# "openrouter/anthropic/claude-3-5-sonnet"
# "openrouter/meta-llama/llama-2-70b-chat"
```

**Usage Example:**
```python
from litellm import completion

response = completion(
    model="openrouter/openai/gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    transforms=[""],  # Optional OpenRouter params
    route=""  # Optional routing
)
```

### 2. OpenAI
**API Key Configuration:**
```python
import os
os.environ["OPENAI_API_KEY"] = "your-api-key"
os.environ["OPENAI_API_BASE"] = "https://api.openai.com/v1"  # Optional
```

**Model Naming Convention:**
```python
model = "gpt-4"  # Direct model name
# or with prefix:
model = "openai/gpt-4"
```

### 3. Anthropic
**API Key Configuration:**
```python
import os
os.environ["ANTHROPIC_API_KEY"] = "your-api-key"
```

**Model Naming Convention:**
```python
model = "anthropic/claude-3-5-sonnet-20240620"
# Supported models:
# - claude-sonnet-4-5-20250929
# - claude-opus-4-5-20251101
# - claude-3-5-sonnet-20240620
# - claude-3-haiku-20240307
```

**Usage Example:**
```python
from litellm import completion

response = completion(
    model="anthropic/claude-3-5-sonnet-20240620",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=4096  # Required for Anthropic
)
```

### 4. Google (Gemini AI Studio)
**API Key Configuration:**
```python
import os
os.environ["GEMINI_API_KEY"] = "your-api-key"
```

**Model Naming Convention:**
```python
model = "gemini/gemini-2.0-flash"
# vs Vertex AI (requires GCP auth):
model = "vertex_ai/gemini-2.0-flash"
```

**Usage Example:**
```python
from litellm import completion

response = completion(
    model="gemini/gemini-2.0-flash",
    messages=[{"role": "user", "content": "Hello"}],
    reasoning_effort="none"  # Cost optimization
)
```

### 5. Groq
**API Key Configuration:**
```python
import os
os.environ["GROQ_API_KEY"] = "your-api-key"
```

**Model Naming Convention:**
```python
model = "groq/llama3-8b-8192"
# All Groq models supported with prefix
```

**Usage Example:**
```python
from litellm import completion

response = completion(
    model="groq/llama3-8b-8192",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True
)
```

### 6. SambaNova
**API Key Configuration:**
```python
import os
os.environ["SAMBANOVA_API_KEY"] = "your-api-key"
```

**Model Naming Convention:**
```python
model = "sambanova/Llama-4-Maverick-17B-128E-Instruct"
# All SambaNova models supported with prefix
```

**Usage Example:**
```python
from litellm import completion

response = completion(
    model="sambanova/Llama-4-Maverick-17B-128E-Instruct",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=10,
    temperature=0.2
)
```

## Multi-Provider Configuration

### Environment Variables Setup
```python
import os

# OpenRouter
os.environ["OPENROUTER_API_KEY"] = "sk-or-..."
os.environ["OR_SITE_URL"] = "https://yoursite.com"
os.environ["OR_APP_NAME"] = "YourApp"

# OpenAI
os.environ["OPENAI_API_KEY"] = "sk-..."

# Anthropic
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

# Google Gemini
os.environ["GEMINI_API_KEY"] = "AI..."

# Groq
os.environ["GROQ_API_KEY"] = "gsk_..."

# SambaNova
os.environ["SAMBANOVA_API_KEY"] = "..."
```

### Configuration File Approach
```yaml
# config.yaml
model_list:
  - model_name: gpt-4
    litellm_params:
      model: openai/gpt-4
      api_key: os.environ/OPENAI_API_KEY
      
  - model_name: claude-3-5-sonnet
    litellm_params:
      model: anthropic/claude-3-5-sonnet-20240620
      api_key: os.environ/ANTHROPIC_API_KEY
      
  - model_name: gemini-flash
    litellm_params:
      model: gemini/gemini-2.0-flash
      api_key: os.environ/GEMINI_API_KEY
      
  - model_name: llama-groq
    litellm_params:
      model: groq/llama3-8b-8192
      api_key: os.environ/GROQ_API_KEY
```

## Security Best Practices

### 1. Environment Variable Management
```python
import os
from dotenv import load_dotenv

# Load from .env file
load_dotenv()

# Validate required keys
required_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
for key in required_keys:
    if not os.getenv(key):
        raise ValueError(f"Missing required environment variable: {key}")
```

### 2. API Key Rotation
```python
import os
from datetime import datetime, timedelta

class APIKeyManager:
    def __init__(self):
        self.keys = {
            "openai": os.getenv("OPENAI_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY")
        }
        
    def rotate_key(self, provider, new_key):
        """Rotate API key for a provider"""
        self.keys[provider] = new_key
        os.environ[f"{provider.upper()}_API_KEY"] = new_key
```

### 3. Rate Limiting & Error Handling
```python
from litellm import completion
import time
from typing import List, Dict

def safe_completion(model: str, messages: List[Dict], max_retries: int = 3):
    """Safe completion with retry logic"""
    for attempt in range(max_retries):
        try:
            response = completion(
                model=model,
                messages=messages,
                timeout=30  # 30 second timeout
            )
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)  # Exponential backoff
```

### 4. Provider Fallback Strategy
```python
from litellm import completion

def completion_with_fallback(messages, providers=None):
    """Try multiple providers in order"""
    if providers is None:
        providers = [
            "openai/gpt-4",
            "anthropic/claude-3-5-sonnet-20240620",
            "groq/llama3-8b-8192"
        ]
    
    for model in providers:
        try:
            return completion(model=model, messages=messages)
        except Exception as e:
            print(f"Failed with {model}: {e}")
            continue
    
    raise Exception("All providers failed")
```

## Implementation Examples

### Basic Multi-Provider Setup
```python
from litellm import completion
import os

# Configure all providers
providers = {
    "openai": "gpt-4",
    "anthropic": "anthropic/claude-3-5-sonnet-20240620",
    "groq": "groq/llama3-8b-8192",
    "gemini": "gemini/gemini-2.0-flash"
}

def get_completion(provider, messages):
    model = providers.get(provider)
    if not model:
        raise ValueError(f"Unknown provider: {provider}")
    
    return completion(model=model, messages=messages)
```

### Advanced Configuration with Proxy
```python
from litellm import Router

# Initialize router with multiple models
model_list = [
    {
        "model_name": "gpt-4",
        "litellm_params": {
            "model": "openai/gpt-4",
            "api_key": os.environ["OPENAI_API_KEY"]
        }
    },
    {
        "model_name": "claude-3-5-sonnet",
        "litellm_params": {
            "model": "anthropic/claude-3-5-sonnet-20240620",
            "api_key": os.environ["ANTHROPIC_API_KEY"]
        }
    }
]

router = Router(model_list=model_list)

# Use router for load balancing
response = router.completion(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
```

## Common Patterns

### 1. Model Selection by Task
```python
def select_model_by_task(task_type):
    task_models = {
        "coding": "openai/gpt-4",
        "analysis": "anthropic/claude-3-5-sonnet-20240620",
        "speed": "groq/llama3-8b-8192",
        "cost": "gemini/gemini-2.0-flash"
    }
    return task_models.get(task_type, "openai/gpt-4")
```

### 2. Cost Optimization
```python
def cost_optimized_completion(messages, budget="low"):
    cost_tiers = {
        "low": "groq/llama3-8b-8192",
        "medium": "gemini/gemini-2.0-flash", 
        "high": "openai/gpt-4"
    }
    
    model = cost_tiers.get(budget, "groq/llama3-8b-8192")
    return completion(model=model, messages=messages)
```

This comprehensive setup provides a robust foundation for multi-provider LLM integration with proper security practices and flexible configuration options.