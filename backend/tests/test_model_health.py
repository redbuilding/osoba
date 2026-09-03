"""Tests for the model health sweep engine (services/model_health.py)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import model_health


def _ok_result(model="openai/gpt-5.6-sol", provider="openai", latency=812):
    return {
        "model": model,
        "provider": provider,
        "status": "ok",
        "latency_ms": latency,
        "text": "Hello! I'm ready to help.",
        "error": None,
    }


def _error_result(model="anthropic/claude-sonnet-5", provider="anthropic"):
    return {
        "model": model,
        "provider": provider,
        "status": "error",
        "latency_ms": 1500,
        "text": None,
        "error": "AuthenticationError: invalid api key",
    }


@pytest.mark.asyncio
async def test_test_single_model_success():
    with patch.object(model_health, "chat_with_provider", new=AsyncMock(return_value="Hello world.")):
        result = await model_health.test_single_model("openai", "openai/gpt-5.6-sol")
    assert result["status"] == "ok"
    assert result["text"] == "Hello world."
    assert result["error"] is None
    assert result["latency_ms"] >= 0
    assert result["model"] == "openai/gpt-5.6-sol"


@pytest.mark.asyncio
async def test_test_single_model_raises_error():
    with patch.object(model_health, "chat_with_provider", new=AsyncMock(side_effect=RuntimeError("boom"))):
        result = await model_health.test_single_model("openai", "openai/gpt-5.6-sol")
    assert result["status"] == "error"
    assert "boom" in result["error"]


@pytest.mark.asyncio
async def test_test_single_model_timeout():
    async def never(*args, **kwargs):
        await asyncio.sleep(5)

    with patch.object(model_health, "chat_with_provider", new=never):
        result = await model_health.test_single_model("openai", "openai/gpt-5.6-sol", timeout=0.01)
    assert result["status"] == "timeout"
    assert "Timed out" in result["error"]


@pytest.mark.asyncio
async def test_test_single_model_empty_response():
    with patch.object(model_health, "chat_with_provider", new=AsyncMock(return_value="   ")):
        result = await model_health.test_single_model("openai", "openai/gpt-5.6-sol")
    assert result["status"] == "empty"


@pytest.mark.asyncio
async def test_run_model_sweep_skips_unconfigured_providers():
    models_by_provider = {
        "openai": ["gpt-5.6-sol", "gpt-5.6-luna"],
        "openrouter": ["openrouter/z-ai/glm-5.3"],
        "ollama": ["llama3.1", "mistral"],
    }
    provider_status = {
        "openai": {"configured": True},
        "openrouter": {"configured": False},
        "ollama": {},
    }

    async def fake_provider_status(provider_id, user_id="default"):
        return provider_status.get(provider_id, {})

    results = []

    async def fake_test(provider_id, full_model, timeout=model_health.SWEEP_TIMEOUT_SECONDS, user_id="default"):
        results.append(full_model)
        return _ok_result(model=full_model, provider=provider_id)

    with patch.object(model_health, "get_available_models_by_provider", new=AsyncMock(return_value=models_by_provider)), \
         patch.object(model_health, "get_provider_status", new=fake_provider_status), \
         patch.object(model_health, "test_single_model", new=fake_test):
        output = await model_health.run_model_sweep(include_ollama=True)

    assert len(output) == 4  # openai 2 + ollama 2 (openrouter skipped)
    assert "openrouter/z-ai/glm-5.3" not in results
    assert all(r["model"] in results for r in output)


@pytest.mark.asyncio
async def test_run_model_sweep_excludes_ollama_when_disabled():
    models_by_provider = {"ollama": ["llama3.1"], "openai": ["gpt-5.6-sol"]}

    with patch.object(model_health, "get_available_models_by_provider", new=AsyncMock(return_value=models_by_provider)), \
         patch.object(model_health, "get_provider_status", new=AsyncMock(return_value={"configured": True})), \
         patch.object(model_health, "test_single_model", new=AsyncMock(return_value=_ok_result())):
        output = await model_health.run_model_sweep(include_ollama=False)

    assert len(output) == 1
    assert output[0]["model"] == "openai/gpt-5.6-sol"


def test_build_summary():
    results = [_ok_result(), _ok_result(latency=200), _error_result()]
    summary = model_health.build_summary(results)
    assert summary["total"] == 3
    assert summary["ok"] == 2
    assert summary["failed"] == 1
    assert summary["avg_latency_ms"] == 506  # (812 + 200) / 2
    assert summary["providers"] == ["anthropic", "openai"]


def test_build_summary_empty():
    summary = model_health.build_summary([])
    assert summary["total"] == 0
    assert summary["ok"] == 0
    assert summary["avg_latency_ms"] is None


def test_build_report_markdown():
    results = [_ok_result(), _error_result()]
    summary = model_health.build_summary(results)
    report = model_health.build_report_markdown(results, summary)
    assert "Model Diagnostics" in report
    assert "openai/gpt-5.6-sol" in report
    assert "anthropic/claude-sonnet-5" in report
    assert "AuthenticationError" in report


def test_build_report_markdown_no_models():
    summary = model_health.build_summary([])
    report = model_health.build_report_markdown([], summary)
    assert "No models tested" in report


def test_persist_report_existing_conversation():
    collection = MagicMock()
    collection.find_one.return_value = {"_id": "abc"}

    with patch("db.mongodb.conversations_collection", collection):
        conv_id = model_health.persist_report(
            "507f1f77bcf86cd799439011", "# report", [_ok_result()], {"total": 1}
        )

    assert conv_id == "507f1f77bcf86cd799439011"
    collection.update_one.assert_called_once()
    args = collection.update_one.call_args[0]
    assert "$push" in args[1]
    pushed = args[1]["$push"]["messages"]
    assert pushed["type"] == "model_test"
    assert pushed["model_test"] == [_ok_result()]


def test_persist_report_creates_new_conversation():
    collection = MagicMock()
    collection.find_one.return_value = None
    collection.insert_one.return_value.inserted_id = "507f1f77bcf86cd799439999"

    with patch("db.mongodb.conversations_collection", collection):
        conv_id = model_health.persist_report(None, "# report", [], {"total": 0})

    assert conv_id == "507f1f77bcf86cd799439999"
    inserted = collection.insert_one.call_args[0][0]
    assert inserted["title"] == "Model Diagnostics"
    assert inserted["messages"][0]["type"] == "model_test"


def test_persist_report_mongodb_unavailable():
    with patch("db.mongodb.conversations_collection", None):
        conv_id = model_health.persist_report(None, "# report", [], {"total": 0})
    assert conv_id is None