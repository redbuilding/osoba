"""
Model health sweep.

Runs a minimal real call against every configured model (plus optional Ollama
models) so we can confirm each one works and surfaces a readable reply. Results
are returned as structured records, summarized, rendered as a markdown report,
and optionally persisted into a chat conversation as a structured `model_test`
message.

Sequential by default to stay gentle on provider rate limits.
"""
import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from core.config import get_logger
from core.providers import get_model_with_prefix
from services.provider_service import (
    chat_with_provider,
    get_available_models_by_provider,
    get_provider_status,
)

logger = get_logger("model_health")

TEST_SYSTEM_PROMPT = "You are a helpful assistant. Be concise."
TEST_USER_PROMPT = "Reply with exactly one short sentence that starts with 'Hello'."
SWEEP_TIMEOUT_SECONDS = 30
MAX_SNIPPET_CHARS = 300

STATUS_ICONS = {"ok": "✅", "error": "❌", "timeout": "⏱️", "empty": "⚠️"}


async def test_single_model(
    provider_id: str,
    full_model: str,
    timeout: float = SWEEP_TIMEOUT_SECONDS,
    user_id: str = "default",
) -> Dict[str, Any]:
    """Run one real minimal call against a single model and record the outcome."""
    messages = [
        {"role": "system", "content": TEST_SYSTEM_PROMPT},
        {"role": "user", "content": TEST_USER_PROMPT},
    ]
    started = time.monotonic()
    status = "ok"
    text = None
    error = None
    try:
        raw = await asyncio.wait_for(
            chat_with_provider(messages, full_model, user_id=user_id, raise_on_error=True),
            timeout=timeout,
        )
        text = (raw or "").strip()[:MAX_SNIPPET_CHARS]
        if not text:
            status = "empty"
            error = "Model returned an empty response"
    except asyncio.TimeoutError:
        status = "timeout"
        error = f"Timed out after {timeout}s"
    except Exception as e:
        status = "error"
        error = str(e)[:MAX_SNIPPET_CHARS]
    latency_ms = int((time.monotonic() - started) * 1000)
    return {
        "model": full_model,
        "provider": provider_id,
        "status": status,
        "latency_ms": latency_ms,
        "text": text,
        "error": error,
    }


async def run_model_sweep(
    user_id: str = "default",
    include_ollama: bool = True,
    timeout: float = SWEEP_TIMEOUT_SECONDS,
) -> List[Dict[str, Any]]:
    """Test every configured provider's models (and optionally Ollama) sequentially."""
    models_by_provider = await get_available_models_by_provider()
    results: List[Dict[str, Any]] = []
    for provider_id, models in models_by_provider.items():
        if provider_id == "ollama":
            if not include_ollama:
                continue
        else:
            status = await get_provider_status(provider_id, user_id)
            if not status.get("configured"):
                logger.info(f"[model_health] Skipping unconfigured provider: {provider_id}")
                continue
        for model in models:
            full_model = get_model_with_prefix(provider_id, model)
            logger.info(f"[model_health] Testing {full_model} ...")
            results.append(
                await test_single_model(provider_id, full_model, timeout=timeout, user_id=user_id)
            )
    return results


def build_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate sweep results into a small summary dict."""
    total = len(results)
    ok = sum(1 for r in results if r["status"] == "ok")
    ok_latencies = [r["latency_ms"] for r in results if r["status"] == "ok"]
    avg_latency_ms = int(sum(ok_latencies) / len(ok_latencies)) if ok_latencies else None
    return {
        "total": total,
        "ok": ok,
        "failed": total - ok,
        "avg_latency_ms": avg_latency_ms,
        "providers": sorted({r["provider"] for r in results}),
    }


def build_report_markdown(results: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
    """Render a human-readable markdown report from sweep results."""
    lines = ["## 🧪 Model Diagnostics", ""]
    if summary["total"]:
        lines.append(
            f"Tested {summary['total']} models across {len(summary['providers'])} provider(s) — "
            f"{summary['ok']} ok, {summary['failed']} failed."
        )
    else:
        lines.append("No models tested (no configured providers).")
    lines.append("")
    if summary.get("avg_latency_ms") is not None:
        lines.append(f"Avg latency (ok): {summary['avg_latency_ms']} ms")
        lines.append("")
    lines.append("| Status | Model | Result |")
    lines.append("|---|---|---|")
    for r in results:
        icon = STATUS_ICONS.get(r["status"], "❓")
        if r["status"] == "ok":
            detail = f"{r['latency_ms']} ms"
            if r.get("text"):
                detail += f" — {r['text']}"
        else:
            detail = r.get("error") or r["status"]
        lines.append(f"| {icon} | `{r['model']}` | {detail} |")
    return "\n".join(lines)


def persist_report(
    conversation_id: Optional[str],
    report_markdown: str,
    results: List[Dict[str, Any]],
    summary: Dict[str, Any],
    user_id: str = "default",
) -> Optional[str]:
    """
    Append the diagnostics report to a conversation, or create a new
    "Model Diagnostics" conversation when no valid conversation id is given.
    Returns the conversation id string, or None when MongoDB is unavailable.
    """
    from db.mongodb import conversations_collection

    if conversations_collection is None:
        return None

    now = datetime.now(timezone.utc)
    message = {
        "role": "assistant",
        "content": report_markdown,
        "is_html": False,
        "type": "model_test",
        "model_test": results,
        "summary": summary,
        "timestamp": now,
    }

    if conversation_id and ObjectId.is_valid(conversation_id):
        conv = conversations_collection.find_one({"_id": ObjectId(conversation_id)})
        if conv:
            conversations_collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$push": {"messages": message}, "$set": {"updated_at": now}},
            )
            return conversation_id

    new_doc = {
        "title": "Model Diagnostics",
        "created_at": now,
        "updated_at": now,
        "messages": [message],
        "model_name": None,
        "user_id": user_id,
    }
    res = conversations_collection.insert_one(new_doc)
    return str(res.inserted_id)