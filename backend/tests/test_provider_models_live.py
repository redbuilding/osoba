"""
Live API test: stream a short response from each model and check for repetition.
Run: cd backend && python -m pytest tests/test_provider_models_live.py -v -s
Requires: API keys configured in the app (MongoDB must be reachable for settings_crud).
"""
import asyncio
import re
import sys
import os
import pytest

# Add backend to path and load .env before any app imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from services.provider_service import stream_chat_with_provider

PROMPT = [
    {"role": "system", "content": "You are a helpful assistant. Be concise."},
    {"role": "user", "content": "Explain what an API is in exactly 3 sentences."},
]

MODELS = {
    "openai": [
        "openai/gpt-5.2",
        "openai/gpt-5-nano",
        "openai/gpt-5",
        "openai/gpt-4.1",
    ],
    "anthropic": [
        "anthropic/claude-opus-4-5",
        "anthropic/claude-sonnet-4-5",
        "anthropic/claude-haiku-4-5",
    ],
    "openrouter": [
        "openrouter/moonshotai/kimi-k2.5",
        "openrouter/z-ai/glm-4.7",
        "openrouter/z-ai/glm-4.7-flash",
        "openrouter/qwen/qwen3-max",
        "openrouter/qwen/qwen3-coder-plus",
        "openrouter/qwen/qwen3-coder-flash",
        "openrouter/mistralai/mistral-large-2512",
        "openrouter/mistralai/codestral-2508",
        "openrouter/meta-llama/llama-4-maverick",
        "openrouter/meta-llama/llama-4-scout",
        "openrouter/meta-llama/llama-3.3-70b-instruct",
        "openrouter/meta-llama/llama-3.1-405b",
        "openrouter/x-ai/grok-4",
        "openrouter/x-ai/grok-4.1-fast",
        "openrouter/openai/gpt-oss-120b",
        "openrouter/openai/gpt-oss-20b",
    ],
}

ALL_MODELS = [m for models in MODELS.values() for m in models]


def detect_repetition(text: str) -> dict:
    """Check for word-level repetition patterns in output."""
    words = text.lower().split()
    if len(words) < 6:
        return {"repeated": False, "ratio": 0.0, "detail": "too short to judge"}

    # Check for consecutive repeated words (e.g. "the the the")
    consec_repeats = 0
    for i in range(1, len(words)):
        if words[i] == words[i - 1] and len(words[i]) > 2:
            consec_repeats += 1
    consec_ratio = consec_repeats / len(words)

    # Check for repeated n-grams (3-grams)
    trigrams = [" ".join(words[i:i+3]) for i in range(len(words) - 2)]
    if trigrams:
        from collections import Counter
        counts = Counter(trigrams)
        most_common_count = counts.most_common(1)[0][1]
        trigram_ratio = most_common_count / len(trigrams)
    else:
        trigram_ratio = 0.0

    repeated = consec_ratio > 0.15 or trigram_ratio > 0.3
    return {
        "repeated": repeated,
        "consec_ratio": round(consec_ratio, 3),
        "trigram_ratio": round(trigram_ratio, 3),
    }


async def stream_and_collect(model: str) -> dict:
    """Stream from a model, collect full text, and analyze."""
    tokens = []
    error = None
    try:
        async for event in stream_chat_with_provider(PROMPT, model):
            # Parse SSE data lines
            if event.startswith("data: "):
                import json
                payload = json.loads(event[6:].strip())
                if payload.get("type") == "token":
                    tokens.append(payload["content"])
                elif payload.get("type") == "error":
                    error = payload["content"]
    except Exception as e:
        error = str(e)

    full_text = "".join(tokens)
    rep = detect_repetition(full_text) if full_text else {}
    return {
        "model": model,
        "text": full_text[:300],
        "length": len(full_text),
        "tokens": len(tokens),
        "error": error,
        "repetition": rep,
    }


@pytest.mark.parametrize("model", ALL_MODELS, ids=ALL_MODELS)
@pytest.mark.asyncio
async def test_model_stream(model):
    """Stream a short response and verify no repetition."""
    result = await asyncio.wait_for(stream_and_collect(model), timeout=60)

    # Print result for visibility
    status = "❌ ERROR" if result["error"] else ("⚠️ REPEAT" if result["repetition"].get("repeated") else "✅ OK")
    print(f"\n{'='*70}")
    print(f"{status} | {result['model']}")
    print(f"  Tokens: {result['tokens']}  Chars: {result['length']}")
    if result["error"]:
        print(f"  Error: {result['error'][:200]}")
    else:
        print(f"  Repetition: {result['repetition']}")
        print(f"  Text: {result['text'][:200]}...")
    print(f"{'='*70}")

    # Assertions
    assert result["error"] is None, f"Model {model} returned error: {result['error']}"
    assert result["length"] > 0, f"Model {model} returned empty response"
    assert not result["repetition"].get("repeated"), (
        f"Model {model} has repetition: {result['repetition']}"
    )
