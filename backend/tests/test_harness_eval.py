"""
Harness engineering evaluation suite.

Tests serve as both regression guards and before/after benchmarks for the
context-passing improvements. Run with: pytest tests/test_harness_eval.py -v
"""
import asyncio
import json
import os
import sys

import pytest

TESTS_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
for p in (PROJECT_ROOT, BACKEND_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)


# ---------------------------------------------------------------------------
# Eval 1 & 2: Goal intent classification and catalog filtering
# ---------------------------------------------------------------------------

def test_classifier_web_goal():
    from backend.services.task_planner import _classify_goal_intent
    cats = _classify_goal_intent("research the latest trends in AI")
    assert "web" in cats
    assert "llm" in cats
    assert "data" not in cats
    assert "canva" not in cats


def test_classifier_data_goal():
    from backend.services.task_planner import _classify_goal_intent
    cats = _classify_goal_intent("analyze this CSV for outliers and correlation")
    assert "data" in cats
    assert "llm" in cats
    assert "canva" not in cats


def test_classifier_image_goal():
    from backend.services.task_planner import _classify_goal_intent
    cats = _classify_goal_intent("generate an image of a sunset over the ocean")
    assert "poe" in cats
    assert "llm" in cats


def test_classifier_email_goal():
    from backend.services.task_planner import _classify_goal_intent
    cats = _classify_goal_intent("write a marketing email newsletter for our product launch")
    assert "hubspot" in cats
    assert "llm" in cats


def test_classifier_design_goal():
    from backend.services.task_planner import _classify_goal_intent
    cats = _classify_goal_intent("create an instagram post design in Canva")
    assert "canva" in cats
    assert "llm" in cats
    assert "data" not in cats


def test_classifier_fallback_default():
    from backend.services.task_planner import _classify_goal_intent
    cats = _classify_goal_intent("do something useful")
    assert "web" in cats  # fallback
    assert "llm" in cats


def test_catalog_web_only_excludes_irrelevant():
    from backend.services.task_planner import _classify_goal_intent, _tool_catalog_text
    cats = _classify_goal_intent("search the web for Python tips")
    catalog = _tool_catalog_text(cats)
    assert "Web Search" in catalog
    assert "LLM-only" in catalog
    assert "Python Data Analysis" not in catalog
    assert "Canva Design" not in catalog
    assert "Figma Design" not in catalog
    assert "HubSpot" not in catalog
    assert "Codex" not in catalog


def test_catalog_full_when_no_categories():
    from backend.services.task_planner import _tool_catalog_text
    full = _tool_catalog_text(None)
    assert "Python Data Analysis" in full
    assert "Canva Design" in full
    assert "Figma Design" in full
    assert "HubSpot" in full
    assert "Codex" in full


def test_filtered_catalog_smaller_than_full():
    from backend.services.task_planner import _classify_goal_intent, _tool_catalog_text
    cats = _classify_goal_intent("research AI trends and write a summary")
    filtered = _tool_catalog_text(cats)
    full = _tool_catalog_text(None)
    assert len(filtered) < len(full), (
        f"Filtered catalog ({len(filtered)} chars) should be smaller than full ({len(full)} chars)"
    )


# ---------------------------------------------------------------------------
# Eval 3: Enabled-tool filtering
# ---------------------------------------------------------------------------

def test_enabled_tools_llm_always_present():
    from backend.services.task_planner import get_enabled_tools

    class FakeState:
        mcp_configs = {}

    result = get_enabled_tools(FakeState())
    assert "llm.generate" in result


def test_enabled_tools_excludes_disabled_service():
    from backend.services.task_planner import get_enabled_tools
    from backend.core.config import CANVA_SERVICE_NAME

    class FakeConfig:
        enabled = False

    class FakeState:
        mcp_configs = {CANVA_SERVICE_NAME: FakeConfig()}

    result = get_enabled_tools(FakeState())
    assert "create_design" not in result
    assert "list_designs" not in result


def test_enabled_tools_includes_enabled_service():
    from backend.services.task_planner import get_enabled_tools
    from backend.core.config import WEB_SEARCH_SERVICE_NAME

    class FakeConfig:
        enabled = True

    class FakeState:
        mcp_configs = {WEB_SEARCH_SERVICE_NAME: FakeConfig()}

    result = get_enabled_tools(FakeState())
    assert "web_search" in result
    assert "smart_search_extract" in result


# ---------------------------------------------------------------------------
# Eval 4: Context extraction — no Python repr noise
# ---------------------------------------------------------------------------

def test_extract_step_text_plain_text():
    from backend.services.task_runner import _extract_step_text
    outputs = {"text": "Here are the results of the analysis."}
    texts = _extract_step_text(outputs)
    assert len(texts) == 1
    assert texts[0] == "Here are the results of the analysis."


def test_extract_step_text_mcp_list_response():
    from backend.services.task_runner import _extract_step_text
    outputs = {"raw": [{"type": "text", "content": "Found 3 relevant results."}]}
    texts = _extract_step_text(outputs)
    assert any("Found 3 relevant results" in t for t in texts)


def test_extract_step_text_raw_dict_excluded():
    from backend.services.task_runner import _extract_step_text
    outputs = {"raw": {"status": "ok", "items": [1, 2, 3], "nested": {"deep": "value"}}}
    texts = _extract_step_text(outputs)
    # Should not fall back to str(dict) — raw dicts are skipped
    assert not any("{'status'" in t or "\"status\"" in t for t in texts)


def test_extract_step_text_raw_string():
    from backend.services.task_runner import _extract_step_text
    outputs = {"raw": "Plain string from tool."}
    texts = _extract_step_text(outputs)
    assert any("Plain string" in t for t in texts)


def test_extract_step_text_per_item_cap():
    from backend.services.task_runner import _extract_step_text
    long_text = "x" * 5000
    outputs = {"raw": [{"type": "text", "content": long_text}]}
    texts = _extract_step_text(outputs)
    assert all(len(t) <= 2000 for t in texts)


def test_build_llm_context_no_python_repr():
    from backend.services.task_runner import _build_llm_context
    task_doc = {
        "plan": {
            "steps": [
                {
                    "title": "Step 1",
                    "tool": "web_search",
                    "outputs": {"raw": {"status": "ok", "organic_results": [{"title": "AI News"}]}},
                }
            ]
        }
    }
    ctx = _build_llm_context(task_doc, upto_index=1)
    # Should not contain Python dict repr
    assert "{'status'" not in ctx
    assert "organic_results" not in ctx or "AI News" in ctx or ctx == ""


# ---------------------------------------------------------------------------
# Eval 5: Plan map helper
# ---------------------------------------------------------------------------

def test_build_plan_map_labels():
    from backend.services.task_runner import _build_plan_map
    steps = [
        {"title": "Search", "tool": "web_search"},
        {"title": "Extract", "tool": "llm.generate"},
        {"title": "Write", "tool": "llm.generate"},
    ]
    result = _build_plan_map(steps, current_idx=1)
    assert "DONE" in result
    assert "YOU ARE HERE" in result
    assert "NEXT" in result
    assert "Step 1 (DONE)" in result
    assert "Step 2 (YOU ARE HERE)" in result
    assert "Step 3 (NEXT)" in result


def test_build_plan_map_first_step():
    from backend.services.task_runner import _build_plan_map
    steps = [
        {"title": "Search", "tool": "web_search"},
        {"title": "Write", "tool": "llm.generate"},
    ]
    result = _build_plan_map(steps, current_idx=0)
    assert "Step 1 (YOU ARE HERE)" in result
    assert "Step 2 (NEXT)" in result


def test_build_plan_map_last_step():
    from backend.services.task_runner import _build_plan_map
    steps = [
        {"title": "Search", "tool": "web_search"},
        {"title": "Write", "tool": "llm.generate"},
    ]
    result = _build_plan_map(steps, current_idx=1)
    assert "Step 1 (DONE)" in result
    assert "Step 2 (YOU ARE HERE)" in result
    assert "UPCOMING" not in result


# ---------------------------------------------------------------------------
# Eval 6: Synthesis function
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_synthesize_context_returns_result(monkeypatch):
    from backend.services.task_runner import _synthesize_context

    async def fake_chat(messages, model):
        return "Key facts: Python is popular. Django is a web framework."

    monkeypatch.setattr("backend.services.task_runner.chat_with_provider", fake_chat)

    result = await _synthesize_context(
        goal="Write a summary of Python web frameworks",
        current_synthesis="",
        step_title="Web search",
        step_output_text="Python is widely used. Django and Flask are popular frameworks.",
        model="test-model",
    )
    assert "Django" in result or len(result) > 0


@pytest.mark.asyncio
async def test_synthesize_context_fallback_on_empty(monkeypatch):
    from backend.services.task_runner import _synthesize_context

    async def fake_chat(messages, model):
        return ""

    monkeypatch.setattr("backend.services.task_runner.chat_with_provider", fake_chat)

    prior = "Some prior synthesis."
    result = await _synthesize_context(
        goal="Test goal",
        current_synthesis=prior,
        step_title="Step 1",
        step_output_text="Some output",
        model="test-model",
    )
    assert result == prior  # Falls back to prior synthesis when LLM returns empty


# ---------------------------------------------------------------------------
# Eval 7: Planning prompt includes filtered catalog
# ---------------------------------------------------------------------------

def test_planning_prompt_web_goal_excludes_data_section():
    from backend.services.task_planner import build_planning_prompt
    prompt = build_planning_prompt(
        goal="research the latest AI news",
        allowed_tools=["web_search", "smart_search_extract", "llm.generate"],
        budget=None,
    )
    assert "Web Search" in prompt
    assert "Python Data Analysis" not in prompt
    assert "Canva Design" not in prompt


def test_planning_prompt_data_goal_includes_data_section():
    from backend.services.task_planner import build_planning_prompt
    prompt = build_planning_prompt(
        goal="analyze this CSV dataset for outliers",
        allowed_tools=["python.load_csv", "python.detect_outliers", "llm.generate"],
        budget=None,
    )
    assert "Python Data Analysis" in prompt
    assert "Web Search" not in prompt


# ---------------------------------------------------------------------------
# Eval 8: Baseline metrics snapshot (informational — always passes)
# ---------------------------------------------------------------------------

HARNESS_EVAL_GOALS = [
    ("web_only",    "research the latest trends in AI and summarize"),
    ("data_only",   "analyze the attached CSV for outliers and statistical patterns"),
    ("design",      "create an instagram post design in Canva"),
    ("email",       "write a marketing email newsletter for our product launch"),
    ("image",       "generate an image of a futuristic cityscape"),
    ("code",        "scaffold a Python FastAPI project with authentication"),
]


def test_baseline_prompt_metrics():
    from backend.services.task_planner import (
        _classify_goal_intent,
        _tool_catalog_text,
        build_planning_prompt,
        ALLOWED_TASK_TOOLS,
    )
    full_catalog_len = len(_tool_catalog_text(None))
    results = []
    for label, goal in HARNESS_EVAL_GOALS:
        cats = _classify_goal_intent(goal)
        filtered_catalog = _tool_catalog_text(cats)
        prompt = build_planning_prompt(goal, ALLOWED_TASK_TOOLS, budget=None)
        results.append({
            "label": label,
            "categories": sorted(cats),
            "filtered_catalog_chars": len(filtered_catalog),
            "full_catalog_chars": full_catalog_len,
            "prompt_chars": len(prompt),
            "reduction_pct": round(100 * (1 - len(filtered_catalog) / full_catalog_len), 1),
        })

    # Print for human review
    print("\n=== Harness Eval: Planning Prompt Size Baseline ===")
    for r in results:
        print(f"[{r['label']}] categories={r['categories']}")
        print(f"  catalog: {r['filtered_catalog_chars']} / {r['full_catalog_chars']} chars ({r['reduction_pct']}% reduction)")
        print(f"  prompt:  {r['prompt_chars']} chars total")

    # All goals should produce a filtered catalog smaller than the full one
    for r in results:
        assert r["filtered_catalog_chars"] <= r["full_catalog_chars"], (
            f"[{r['label']}] filtered catalog should not exceed full catalog"
        )

    # Always passes — this is a snapshot test for manual comparison before/after
    assert len(results) == len(HARNESS_EVAL_GOALS)
