import json
import pytest
from backend.services.task_planner import ALLOWED_TASK_TOOLS, _normalize_tool, _tool_catalog_text
from backend.services.mcp_service import app_state
from backend.core.config import (
    WEB_SEARCH_SERVICE_NAME,
    MYSQL_DB_SERVICE_NAME,
    YOUTUBE_SERVICE_NAME,
    PYTHON_SERVICE_NAME,
    HUBSPOT_SERVICE_NAME,
    CODEX_SERVICE_NAME,
)


def test_tool_count():
    """Verify we have 30+ tools in the whitelist"""
    assert len(ALLOWED_TASK_TOOLS) >= 30, f"Expected 30+ tools, got {len(ALLOWED_TASK_TOOLS)}"


def test_web_search_tools():
    """Verify all web search tools are available"""
    assert "web_search" in ALLOWED_TASK_TOOLS
    assert "smart_search_extract" in ALLOWED_TASK_TOOLS
    assert "image_search" in ALLOWED_TASK_TOOLS
    assert "news_search" in ALLOWED_TASK_TOOLS


def test_python_tools():
    """Verify all 17 Python analysis tools are available"""
    python_tools = [t for t in ALLOWED_TASK_TOOLS if t.startswith("python.")]
    assert len(python_tools) == 17, f"Expected 17 Python tools, got {len(python_tools)}"
    
    # Data loading
    assert "python.load_csv" in ALLOWED_TASK_TOOLS
    
    # Data inspection
    assert "python.get_head" in ALLOWED_TASK_TOOLS
    assert "python.get_data_info" in ALLOWED_TASK_TOOLS
    assert "python.get_descriptive_statistics" in ALLOWED_TASK_TOOLS
    assert "python.get_value_counts" in ALLOWED_TASK_TOOLS
    assert "python.get_correlation_matrix" in ALLOWED_TASK_TOOLS
    
    # Data cleaning
    assert "python.check_missing_values" in ALLOWED_TASK_TOOLS
    assert "python.handle_missing_values" in ALLOWED_TASK_TOOLS
    assert "python.detect_outliers" in ALLOWED_TASK_TOOLS
    assert "python.convert_data_types" in ALLOWED_TASK_TOOLS
    
    # Data transformation
    assert "python.rename_columns" in ALLOWED_TASK_TOOLS
    assert "python.drop_columns" in ALLOWED_TASK_TOOLS
    assert "python.filter_dataframe" in ALLOWED_TASK_TOOLS
    assert "python.group_and_aggregate" in ALLOWED_TASK_TOOLS
    
    # Data analysis
    assert "python.query_dataframe" in ALLOWED_TASK_TOOLS
    assert "python.perform_hypothesis_test" in ALLOWED_TASK_TOOLS
    
    # Visualization
    assert "python.create_plot" in ALLOWED_TASK_TOOLS


def test_hubspot_tools():
    """Verify HubSpot tools are available"""
    assert "create_hubspot_marketing_email" in ALLOWED_TASK_TOOLS
    assert "update_hubspot_marketing_email" in ALLOWED_TASK_TOOLS


def test_codex_tools():
    """Verify all Codex tools are available"""
    codex_tools = [t for t in ALLOWED_TASK_TOOLS if t.startswith("codex.")]
    assert len(codex_tools) >= 6, f"Expected 6+ Codex tools, got {len(codex_tools)}"
    
    assert "codex.run" in ALLOWED_TASK_TOOLS
    assert "codex.create_workspace" in ALLOWED_TASK_TOOLS
    assert "codex.start_codex_run" in ALLOWED_TASK_TOOLS
    assert "codex.get_codex_run" in ALLOWED_TASK_TOOLS
    assert "codex.read_file" in ALLOWED_TASK_TOOLS
    assert "codex.get_manifest" in ALLOWED_TASK_TOOLS


def test_tool_aliases():
    """Verify tool aliases work correctly"""
    assert _normalize_tool("smart_extract") == "smart_search_extract"
    assert _normalize_tool("smart_search") == "smart_search_extract"
    assert _normalize_tool("outliers") == "python.detect_outliers"
    assert _normalize_tool("correlation") == "python.get_correlation_matrix"
    assert _normalize_tool("hubspot_email") == "create_hubspot_marketing_email"


def test_tool_catalog_completeness():
    """Verify tool catalog text includes all tools"""
    catalog = _tool_catalog_text()
    
    # Check for key tools
    assert "smart_search_extract" in catalog
    assert "detect_outliers" in catalog
    assert "perform_hypothesis_test" in catalog
    assert "create_hubspot_marketing_email" in catalog
    assert "codex.run" in catalog
    
    # Check for tool categories
    assert "Web Search" in catalog or "web search" in catalog.lower()
    assert "Python" in catalog or "python" in catalog.lower()
    assert "HubSpot" in catalog or "hubspot" in catalog.lower()
    assert "Codex" in catalog or "codex" in catalog.lower()


def test_mcp_service_config_alignment():
    """Verify ALLOWED_TASK_TOOLS aligns with MCP service configs"""
    # Web Search
    web_tools = app_state.mcp_configs[WEB_SEARCH_SERVICE_NAME].required_tools
    for tool in web_tools:
        assert tool in ALLOWED_TASK_TOOLS, f"Web search tool {tool} missing from whitelist"
    
    # Python
    python_tools = app_state.mcp_configs[PYTHON_SERVICE_NAME].required_tools
    for tool in python_tools:
        assert f"python.{tool}" in ALLOWED_TASK_TOOLS, f"Python tool {tool} missing from whitelist"
    
    # HubSpot
    hubspot_tools = app_state.mcp_configs[HUBSPOT_SERVICE_NAME].required_tools
    for tool in hubspot_tools:
        assert tool in ALLOWED_TASK_TOOLS, f"HubSpot tool {tool} missing from whitelist"
    
    # Codex
    codex_tools = app_state.mcp_configs[CODEX_SERVICE_NAME].required_tools
    for tool in codex_tools:
        # Codex tools may use dot notation in whitelist
        assert f"codex.{tool}" in ALLOWED_TASK_TOOLS or tool in ALLOWED_TASK_TOOLS, \
            f"Codex tool {tool} missing from whitelist"


@pytest.mark.asyncio
async def test_plan_with_smart_search(monkeypatch):
    """Verify planner can use smart_search_extract"""
    from backend.services.task_planner import plan_task
    
    # Mock chat_with_provider to return a plan with smart_search_extract
    async def fake_chat(messages, model_name, repeat_penalty=1.15):
        return json.dumps({
            "constraints": [],
            "resources": [],
            "steps": [{
                "id": "s1",
                "title": "Smart search",
                "instruction": "Search for X",
                "tool": "smart_search_extract",
                "params": {"query": "test"},
                "success_criteria": "Found results"
            }]
        })
    
    monkeypatch.setattr("backend.services.task_planner.chat_with_provider", fake_chat)
    
    plan = await plan_task("Research something", model="test", budget=None)
    assert len(plan.steps) > 0
    assert plan.steps[0].tool == "smart_search_extract"


@pytest.mark.asyncio
async def test_plan_with_python_analysis(monkeypatch):
    """Verify planner can use advanced Python tools"""
    from backend.services.task_planner import plan_task
    
    # Mock chat_with_provider to return a plan with advanced Python tools
    async def fake_chat(messages, model_name, repeat_penalty=1.15):
        return json.dumps({
            "constraints": [],
            "resources": [],
            "steps": [
                {
                    "id": "s1",
                    "title": "Load CSV",
                    "instruction": "Load data",
                    "tool": "python.load_csv",
                    "params": {"csv_b64": "test"},
                    "success_criteria": "Loaded"
                },
                {
                    "id": "s2",
                    "title": "Detect outliers",
                    "instruction": "Find outliers",
                    "tool": "python.detect_outliers",
                    "params": {"df_id": "test", "method": "iqr"},
                    "success_criteria": "Found outliers"
                },
                {
                    "id": "s3",
                    "title": "Statistical test",
                    "instruction": "Run t-test",
                    "tool": "python.perform_hypothesis_test",
                    "params": {"df_id": "test", "test_type": "ttest", "col1": "A", "col2": "B"},
                    "success_criteria": "Test completed"
                }
            ]
        })
    
    monkeypatch.setattr("backend.services.task_planner.chat_with_provider", fake_chat)
    
    plan = await plan_task("Analyze CSV with outliers and stats", model="test", budget=None)
    assert len(plan.steps) == 3
    assert plan.steps[0].tool == "python.load_csv"
    assert plan.steps[1].tool == "python.detect_outliers"
    assert plan.steps[2].tool == "python.perform_hypothesis_test"
