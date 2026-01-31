#!/usr/bin/env python3
import requests
import json
import re

def fetch_provider_docs():
    providers = {
        'openrouter': 'https://docs.litellm.ai/docs/providers/openrouter',
        'openai': 'https://docs.litellm.ai/docs/providers/openai',
        'anthropic': 'https://docs.litellm.ai/docs/providers/anthropic',
        'groq': 'https://docs.litellm.ai/docs/providers/groq',
        'sambanova': 'https://docs.litellm.ai/docs/providers/sambanova',
        'gemini': 'https://docs.litellm.ai/docs/providers/gemini'
    }
    
    results = {}
    
    for provider, url in providers.items():
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                content = response.text
                
                # Extract key information using regex
                api_key_pattern = r'(OPENROUTER_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GROQ_API_KEY|SAMBANOVA_API_KEY|GOOGLE_API_KEY|GEMINI_API_KEY)["\']?\s*=\s*["\']([^"\']*)["\']?'
                model_pattern = r'model\s*=\s*["\']([^"\']*)["\']'
                env_pattern = r'os\.environ\[["\']([^"\']*)["\']'
                
                api_keys = re.findall(api_key_pattern, content, re.IGNORECASE)
                models = re.findall(model_pattern, content)
                env_vars = re.findall(env_pattern, content)
                
                results[provider] = {
                    'api_keys': list(set(api_keys)),
                    'models': list(set(models))[:10],  # First 10 models
                    'env_vars': list(set(env_vars))[:10]  # First 10 env vars
                }
                
        except Exception as e:
            results[provider] = {'error': str(e)}
    
    return results

if __name__ == "__main__":
    docs = fetch_provider_docs()
    print(json.dumps(docs, indent=2))