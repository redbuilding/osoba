# Task System MCP Access Analysis

**Date**: February 21, 2026  
**Status**: Feature Parity Assessment

---

## Executive Summary

The task system has **limited MCP tool access** compared to the chat interface. It supports a **whitelist of 10 tools** while the chat interface has access to **all MCP servers and their full tool catalogs** (20+ tools across 5 MCP servers).

**Key Finding**: The task system is **intentionally restricted** for safety and reliability, but this limits its capabilities for complex workflows.

---

## Tool Access Comparison

### Chat Interface (Full Access)

The chat interface (`services/chat_service.py`) has **unrestricted access** to all MCP servers:

| MCP Server | Tools Available | Access Method |
|------------|----------------|---------------|
| **Web Search** | `web_search`, `smart_search_extract`, `image_search`, `news_search` | `_handle_search()` |
| **MySQL Database** | `execute_sql_query_tool` | `_handle_database()` |
| **YouTube** | `get_youtube_transcript` | `_handle_youtube()` |
| **HubSpot** | `create_hubspot_marketing_email`, `update_hubspot_marketing_email` | `_handle_hubspot()` |
| **Python Analysis** | `load_csv`, `get_head`, `create_plot`, `get_descriptive_statistics`, `get_data_info`, `filter_dataframe`, `group_and_aggregate`, `detect_outliers`, `convert_data_types`, `perform_hypothesis_test`, `check_missing_values`, `handle_missing_values`, `get_correlation_matrix`, `get_value_counts`, `query_dataframe`, `rename_columns`, `drop_columns` | `_handle_python()` |
| **Codex Workspace** | `create_workspace`, `start_codex_run`, `get_codex_run`, `read_file`, `get_manifest`, `cleanup_workspace` | Direct API calls |

**Total**: 30+ tools across 6 MCP servers

### Task System (Restricted Access)

The task system (`services/task_planner.py`) uses a **hardcoded whitelist**:

```python
ALLOWED_TASK_TOOLS = [
    "web_search",                          # Web Search MCP
    "execute_sql_query_tool",              # MySQL MCP
    "get_youtube_transcript",              # YouTube MCP
    "python.load_csv",                     # Python MCP
    "python.get_head",                     # Python MCP
    "python.get_descriptive_statistics",   # Python MCP
    "python.create_plot",                  # Python MCP
    "python.query_dataframe",              # Python MCP
    "llm.generate",                        # Direct LLM (no MCP)
    "codex.run",                           # Codex MCP (gated on OpenAI key)
]
```

**Total**: 10 tools (8 MCP tools + 1 LLM-only + 1 Codex)

---

## Missing Tools in Task System

### 1. Web Search Tools (3 missing)
- ❌ `smart_search_extract` - Enhanced content extraction (the chat interface uses this by default!)
- ❌ `image_search` - Image-specific search
- ❌ `news_search` - News-specific search

**Impact**: Tasks can only do basic web search, not the "smart" extraction that chat uses.

### 2. Python Analysis Tools (12 missing)
- ❌ `get_data_info` - DataFrame metadata
- ❌ `filter_dataframe` - Row filtering
- ❌ `group_and_aggregate` - Grouping operations
- ❌ `detect_outliers` - Statistical outlier detection
- ❌ `convert_data_types` - Type conversion
- ❌ `perform_hypothesis_test` - Statistical testing
- ❌ `check_missing_values` - Missing data analysis
- ❌ `handle_missing_values` - Missing data imputation
- ❌ `get_correlation_matrix` - Correlation analysis
- ❌ `get_value_counts` - Frequency analysis
- ❌ `rename_columns` - Column renaming
- ❌ `drop_columns` - Column removal

**Impact**: Tasks can only do basic CSV analysis (load, head, stats, plot, query). No data cleaning, outlier detection, statistical testing, or advanced transformations.

### 3. HubSpot Tools (2 missing)
- ❌ `create_hubspot_marketing_email` - Create marketing emails
- ❌ `update_hubspot_marketing_email` - Update marketing emails

**Impact**: Tasks cannot interact with HubSpot at all, despite it being a core MCP server.

### 4. Codex Tools (5 missing)
- ❌ `create_workspace` - Manual workspace creation
- ❌ `get_codex_run` - Check run status
- ❌ `read_file` - Read workspace files
- ❌ `get_manifest` - Get workspace manifest
- ❌ `cleanup_workspace` - Manual cleanup

**Impact**: Tasks can only use `codex.run` (high-level), not fine-grained workspace management.

---

## Why the Restriction?

### Design Rationale (Inferred)

1. **Safety**: Whitelist prevents tasks from using dangerous or untested tools
2. **Reliability**: Fewer tools = fewer failure modes
3. **Simplicity**: Easier to reason about task behavior with limited toolset
4. **Cost Control**: Prevents runaway API usage (e.g., repeated HubSpot calls)

### Evidence from Code

**Tool Normalization & Aliasing** (`task_planner.py:38-54`):
```python
TOOL_ALIASES = {
    "search": "web_search",
    "web-search": "web_search",
    "google_search": "web_search",
    # ... etc
}
```
This suggests the planner tries to map various tool names to the whitelist, indicating intentional restriction.

**Whitelist Enforcement** (`task_planner.py:159-163`):
```python
tool = _normalize_tool(st.get("tool"))
if tool not in ALLOWED_TASK_TOOLS:
    logger.warning(f"Planner proposed tool not allowed: {st.get('tool')}; skipping step {i}")
    continue
```
Steps with non-whitelisted tools are **silently dropped** from the plan.

**Python Tool Gating** (`task_planner.py:200-217`):
```python
has_csv_load = any(s.tool == "python.load_csv" for s in plan.steps)
if not has_csv_load:
    # Replace python.* tools with llm.generate
```
If no CSV is loaded, Python tools are automatically replaced with LLM generation.

---

## Impact on Task Capabilities

### What Tasks CAN Do
✅ Basic web search (not smart extraction)  
✅ SQL queries (read-only)  
✅ YouTube transcript extraction  
✅ Basic CSV analysis (load, preview, stats, plot, query)  
✅ LLM-only reasoning steps  
✅ Code generation via Codex (if OpenAI configured)  

### What Tasks CANNOT Do
❌ Smart web content extraction (chat uses this by default!)  
❌ Advanced data cleaning (missing values, outliers, type conversion)  
❌ Statistical hypothesis testing  
❌ HubSpot marketing automation  
❌ Image or news-specific searches  
❌ Fine-grained Codex workspace management  

---

## Recommendations

### Option 1: Expand Whitelist (Conservative)
Add the most useful missing tools:

```python
ALLOWED_TASK_TOOLS = [
    # Existing tools
    "web_search",
    "smart_search_extract",  # ← ADD: Chat uses this by default
    "execute_sql_query_tool",
    "get_youtube_transcript",
    
    # Python - Basic (existing)
    "python.load_csv",
    "python.get_head",
    "python.get_descriptive_statistics",
    "python.create_plot",
    "python.query_dataframe",
    
    # Python - Advanced (ADD)
    "python.filter_dataframe",        # ← ADD: Essential for data workflows
    "python.group_and_aggregate",     # ← ADD: Essential for data workflows
    "python.detect_outliers",         # ← ADD: Data quality
    "python.get_correlation_matrix",  # ← ADD: Statistical analysis
    "python.perform_hypothesis_test", # ← ADD: Statistical analysis
    
    # HubSpot (ADD)
    "create_hubspot_marketing_email", # ← ADD: Business automation
    "update_hubspot_marketing_email", # ← ADD: Business automation
    
    # LLM & Codex (existing)
    "llm.generate",
    "codex.run",
]
```

**Pros**: Maintains safety, adds most-requested capabilities  
**Cons**: Still limited, requires manual curation  

### Option 2: Dynamic Tool Discovery (Aggressive)
Remove the whitelist entirely and let tasks use **all available MCP tools**:

```python
async def get_available_task_tools() -> List[str]:
    """Dynamically discover all available MCP tools"""
    tools = ["llm.generate"]  # Always available
    
    # Query each MCP service for its tools
    for service_name in [WEB_SEARCH_SERVICE_NAME, MYSQL_DB_SERVICE_NAME, 
                         YOUTUBE_SERVICE_NAME, PYTHON_SERVICE_NAME, 
                         HUBSPOT_SERVICE_NAME, CODEX_SERVICE_NAME]:
        if app_state.mcp_service_ready.get(service_name):
            # Get tools from service (would need new API)
            service_tools = await get_mcp_service_tools(service_name)
            tools.extend(service_tools)
    
    return tools
```

**Pros**: Full feature parity with chat, no manual curation  
**Cons**: Higher risk of failures, harder to debug, potential cost overruns  

### Option 3: Tiered Access (Hybrid)
Create **safe** and **advanced** tool tiers:

```python
SAFE_TASK_TOOLS = [
    "web_search", "smart_search_extract",
    "execute_sql_query_tool",
    "get_youtube_transcript",
    "python.load_csv", "python.get_head", "python.get_descriptive_statistics",
    "llm.generate",
]

ADVANCED_TASK_TOOLS = [
    "python.filter_dataframe", "python.group_and_aggregate",
    "python.detect_outliers", "python.perform_hypothesis_test",
    "create_hubspot_marketing_email", "update_hubspot_marketing_email",
    "codex.run",
]

# User can opt-in to advanced tools per task
def get_allowed_tools(advanced: bool = False) -> List[str]:
    if advanced:
        return SAFE_TASK_TOOLS + ADVANCED_TASK_TOOLS
    return SAFE_TASK_TOOLS
```

**Pros**: Safety by default, power when needed  
**Cons**: Adds complexity to task creation UI  

---

## Specific Issues

### Issue 1: Chat Uses `smart_search_extract`, Tasks Use `web_search`

**Code Evidence** (`chat_service.py:189-196`):
```python
async def _handle_search(self):
    # Use smart_search_extract for enhanced content extraction
    req_id = await submit_mcp_request(WEB_SEARCH_SERVICE_NAME, "tool", {
        "tool": "smart_search_extract",  # ← Chat uses this
        "params": { ... }
    })
```

**Task Planner** (`task_planner.py:13`):
```python
ALLOWED_TASK_TOOLS = [
    "web_search",  # ← Tasks use basic search only
    # "smart_search_extract" is NOT in the whitelist
]
```

**Impact**: Tasks get inferior search results compared to chat. This is a **major inconsistency**.

**Fix**: Add `smart_search_extract` to `ALLOWED_TASK_TOOLS` immediately.

### Issue 2: Python Tool Catalog Mismatch

**MCP Service Config** (`mcp_service.py:59-62`):
```python
PYTHON_SERVICE_NAME: MCPServiceConfig(
    required_tools=["load_csv", "get_head", "create_plot", "get_descriptive_statistics", 
                    "get_data_info", "filter_dataframe", "group_and_aggregate", 
                    "detect_outliers", "convert_data_types", "perform_hypothesis_test"]
)
```

**Task Planner Whitelist** (`task_planner.py:16-19`):
```python
"python.load_csv",
"python.get_head",
"python.get_descriptive_statistics",
"python.create_plot",
"python.query_dataframe",
# Missing: get_data_info, filter_dataframe, group_and_aggregate, 
#          detect_outliers, convert_data_types, perform_hypothesis_test
```

**Impact**: The Python MCP server advertises 10+ tools, but tasks can only use 5. This creates user confusion ("Why can't my task do what the chat can do?").

### Issue 3: HubSpot Completely Unavailable

**MCP Service Config** (`mcp_service.py:52-56`):
```python
HUBSPOT_SERVICE_NAME: MCPServiceConfig(
    required_tools=["create_hubspot_marketing_email", "update_hubspot_marketing_email"]
)
```

**Task Planner Whitelist**: No HubSpot tools at all.

**Impact**: Tasks cannot automate HubSpot workflows, despite this being a core use case mentioned in the README ("HubSpot business actions").

---

## Business Impact

### For Open-Core Strategy

**Problem**: If you're positioning Osoba as "enterprise-ready" with advanced task automation, the limited tool access is a **competitive weakness**.

**Competitor Comparison**:
- **OpenClaw**: No task system (advantage: Osoba)
- **Cursor/Windsurf**: Full tool access in agentic workflows (disadvantage: Osoba)
- **Cline**: Full MCP access (disadvantage: Osoba)

**Recommendation**: Expand task tool access to match or exceed competitors. This is a **differentiator** for the Pro/Enterprise tiers.

### For Marketing

**Current Messaging** (from README):
> "Long‑Running Tasks (Plan & Execute): Create autonomous tasks that plan and execute multi‑step workflows"

**Reality**: Tasks can only use 10 tools, missing 20+ tools available in chat.

**Risk**: Users will discover the limitation and feel misled. This hurts trust and conversion.

**Fix**: Either expand tool access OR update marketing to be explicit about limitations.

---

## Implementation Effort

### Quick Win (1-2 hours)
Add `smart_search_extract` to whitelist:
```python
ALLOWED_TASK_TOOLS = [
    "web_search",
    "smart_search_extract",  # ← ADD THIS LINE
    # ... rest unchanged
]
```

### Medium Effort (1 day)
Add all Python analysis tools:
```python
ALLOWED_TASK_TOOLS = [
    # ... existing tools ...
    "python.filter_dataframe",
    "python.group_and_aggregate",
    "python.detect_outliers",
    "python.get_correlation_matrix",
    "python.perform_hypothesis_test",
    "python.get_data_info",
    "python.check_missing_values",
    "python.handle_missing_values",
    "python.get_value_counts",
    "python.convert_data_types",
    "python.rename_columns",
    "python.drop_columns",
]
```

### Large Effort (3-5 days)
Dynamic tool discovery with safety controls:
1. Add API to query MCP services for available tools
2. Implement tool risk scoring (safe/moderate/risky)
3. Add per-task tool access controls
4. Update UI to show available tools per task
5. Add usage monitoring and rate limiting

---

## Testing Recommendations

### Test Case 1: Smart Search Parity
**Goal**: Verify tasks can do smart content extraction like chat

**Steps**:
1. Create task: "Research the latest MCP protocol updates"
2. Verify plan includes `smart_search_extract` (not just `web_search`)
3. Compare output quality to chat with same query

**Expected**: Task output should match chat quality

### Test Case 2: Advanced Data Analysis
**Goal**: Verify tasks can do full data workflows

**Steps**:
1. Create task: "Load sales.csv, remove outliers, test correlation between price and sales"
2. Verify plan includes: `load_csv` → `detect_outliers` → `perform_hypothesis_test`
3. Check output includes statistical test results

**Expected**: Task completes without falling back to `llm.generate`

### Test Case 3: HubSpot Automation
**Goal**: Verify tasks can automate marketing workflows

**Steps**:
1. Create task: "Create a HubSpot email campaign for product launch"
2. Verify plan includes `create_hubspot_marketing_email`
3. Check HubSpot API is called correctly

**Expected**: Task creates email in HubSpot

---

## Conclusion

**The task system has intentionally limited MCP tool access (10 tools) compared to the chat interface (30+ tools).** This restriction was likely implemented for safety and reliability, but it creates:

1. **Feature parity issues**: Chat can do things tasks cannot
2. **User confusion**: "Why can't my task do X when chat can?"
3. **Competitive weakness**: Other AI tools offer full tool access in agentic workflows
4. **Marketing misalignment**: README promises "autonomous multi-step workflows" but tools are limited

**Immediate Action**: Add `smart_search_extract` to task whitelist (chat uses this by default, tasks don't).

**Strategic Decision**: Choose between:
- **Conservative**: Expand whitelist to 20-25 most useful tools (recommended for stability)
- **Aggressive**: Remove whitelist entirely, match chat's full access (recommended for competitive positioning)
- **Hybrid**: Tiered access (safe by default, advanced opt-in)

For the **open-core commercial strategy**, I recommend the **aggressive approach** (full tool access) to differentiate Osoba as the most capable MCP task automation platform. This becomes a key selling point for Pro/Enterprise tiers.
