import json
from typing import Dict, List

from core.config import get_logger
from core.models import Plan, PlanStep
from services.provider_service import chat_with_provider
from services.llm_service import get_default_ollama_model


logger = get_logger("task_planner")

ALLOWED_TASK_TOOLS = [
    # Web Search MCP (4 tools)
    "web_search",                    # Basic search
    "smart_search_extract",          # Smart extraction (chat uses this by default!)
    "image_search",                  # Image-specific search
    "news_search",                   # News-specific search
    
    # MySQL Database MCP (1 tool)
    "execute_sql_query_tool",        # Read-only SQL queries
    
    # YouTube MCP (1 tool)
    "get_youtube_transcript",        # Transcript extraction
    
    # Python Analysis MCP (17 tools)
    # Data Loading
    "python.load_csv",               # Load CSV from base64
    
    # Data Inspection
    "python.get_head",               # First N rows
    "python.get_data_info",          # DataFrame metadata
    "python.get_descriptive_statistics",  # Statistical summary
    "python.get_value_counts",       # Frequency analysis
    "python.get_correlation_matrix", # Correlation analysis
    
    # Data Cleaning
    "python.check_missing_values",   # Identify missing data
    "python.handle_missing_values",  # Handle missing data (drop/fill/interpolate)
    "python.detect_outliers",        # Outlier detection (IQR/Z-score)
    "python.convert_data_types",     # Type conversion (datetime/category/numeric)
    
    # Data Transformation
    "python.rename_columns",         # Rename columns
    "python.drop_columns",           # Remove columns
    "python.filter_dataframe",       # Filter rows by condition
    "python.group_and_aggregate",    # Group by and aggregate
    
    # Data Analysis
    "python.query_dataframe",        # Advanced querying
    "python.perform_hypothesis_test", # Statistical testing (t-test/correlation/chi-square)
    
    # Visualization
    "python.create_plot",            # Create plots (scatter/histogram/bar/box)
    
    # HubSpot Business MCP (2 tools)
    "create_hubspot_marketing_email",  # Create marketing emails
    "update_hubspot_marketing_email",  # Update marketing emails
    
    # Codex Workspace MCP (7 tools)
    "codex.run",                     # High-level code generation
    "codex.create_workspace",        # Manual workspace creation
    "codex.start_codex_run",         # Start run manually
    "codex.get_codex_run",           # Check run status
    "codex.read_file",               # Read workspace files
    "codex.get_manifest",            # Get workspace manifest
    "codex.cleanup_workspace",       # Manual cleanup
    
    # LLM-only (no MCP)
    "llm.generate",                  # Direct LLM generation
]

# Back-compat shim for tests that patch chat_with_ollama directly
async def chat_with_ollama(messages, model_name, repeat_penalty=1.15):
    try:
        # If model is unprefixed, assume ollama
        full = model_name if str(model_name).startswith("ollama/") else f"ollama/{model_name}"
        return await chat_with_provider(messages, full, repeat_penalty)
    except Exception:
        return None

# Lightweight tool aliasing to keep plans robust across models
TOOL_ALIASES = {
    # Existing search variants
    "search": "web_search",
    "web-search": "web_search",
    "google_search": "web_search",
    "bing_search": "web_search",
    
    # Smart search variants (NEW)
    "smart_extract": "smart_search_extract",
    "smart_search": "smart_search_extract",
    "extract_content": "smart_search_extract",
    
    # Image search variants (NEW)
    "image": "image_search",
    "images": "image_search",
    "picture_search": "image_search",
    
    # News search variants (NEW)
    "news": "news_search",
    "latest_news": "news_search",
    
    # HubSpot variants (NEW)
    "hubspot_email": "create_hubspot_marketing_email",
    "create_email": "create_hubspot_marketing_email",
    "update_email": "update_hubspot_marketing_email",
    
    # Python data cleaning variants (NEW)
    "missing_values": "python.check_missing_values",
    "outliers": "python.detect_outliers",
    "clean_data": "python.handle_missing_values",
    
    # Python analysis variants (NEW)
    "correlate": "python.get_correlation_matrix",
    "correlation": "python.get_correlation_matrix",
    "hypothesis": "python.perform_hypothesis_test",
    "ttest": "python.perform_hypothesis_test",
    "stats_test": "python.perform_hypothesis_test",
    
    # Existing generation variants
    "write": "llm.generate",
    "compose": "llm.generate",
    "summarize": "llm.generate",
    "generate": "llm.generate",
    "generate_text": "llm.generate",
    "finalize": "llm.generate",
    "draft": "llm.generate",
    "draft_email": "llm.generate",
    "write_email": "llm.generate",
    "compose_email": "llm.generate",
}

def _normalize_tool(name: str | None) -> str | None:
    if not name:
        return None
    key = str(name).strip().lower().replace(" ", "_")
    return TOOL_ALIASES.get(key, key)


def _tool_catalog_text() -> str:
    return (
        "## Web Search Tools\n"
        "- web_search(query: string) -> {status, organic_results...}\n"
        "- smart_search_extract(query: string, max_urls?: int, max_chars_per_url?: int) -> {extracted_content, search_summary}\n"
        "- image_search(query: string) -> {status, images...}\n"
        "- news_search(query: string) -> {status, news_results...}\n"
        "\n"
        "## Database Tools\n"
        "- execute_sql_query_tool(query: string) -> {columns, rows} (read-only SELECT only)\n"
        "\n"
        "## YouTube Tools\n"
        "- get_youtube_transcript(youtube_url: string) -> text\n"
        "\n"
        "## Python Data Analysis Tools\n"
        "# Data Loading\n"
        "- python.load_csv(csv_b64: string) -> text (returns dataframe ID)\n"
        "\n"
        "# Data Inspection\n"
        "- python.get_head(df_id: string, n?: int) -> text (first N rows)\n"
        "- python.get_data_info(df_id: string) -> text (dtypes, memory, non-null counts)\n"
        "- python.get_descriptive_statistics(df_id: string) -> text (mean, std, min, max, quartiles)\n"
        "- python.get_value_counts(df_id: string, column_name: string) -> text (frequency counts)\n"
        "- python.get_correlation_matrix(df_id: string) -> text (correlation between numeric columns)\n"
        "\n"
        "# Data Cleaning\n"
        "- python.check_missing_values(df_id: string) -> text (count of NaN per column)\n"
        "- python.handle_missing_values(df_id: string, strategy: 'drop'|'fill'|'interpolate', columns?: list, value?: any) -> text\n"
        "- python.detect_outliers(df_id: string, method: 'iqr'|'zscore', columns?: list) -> text (outlier indices)\n"
        "- python.convert_data_types(df_id: string, type_map_json: string) -> text (convert column types)\n"
        "\n"
        "# Data Transformation\n"
        "- python.rename_columns(df_id: string, rename_map_json: string) -> text\n"
        "- python.drop_columns(df_id: string, columns_to_drop: list) -> text\n"
        "- python.filter_dataframe(df_id: string, condition: string) -> text (pandas query syntax)\n"
        "- python.group_and_aggregate(df_id: string, group_by: list, agg_functions: string) -> text\n"
        "\n"
        "# Data Analysis\n"
        "- python.query_dataframe(df_id: string, query_string: string) -> text (may return new df_id)\n"
        "- python.perform_hypothesis_test(df_id: string, test_type: 'ttest'|'correlation'|'chisquare', col1: string, col2?: string) -> text\n"
        "\n"
        "# Visualization\n"
        "- python.create_plot(df_id: string, plot_type: 'scatter'|'histogram'|'bar'|'box', x_col: string, y_col?: string) -> image_b64\n"
        "\n"
        "## HubSpot Business Tools\n"
        "- create_hubspot_marketing_email(email_json: string) -> {status, email_id} (requires OAuth)\n"
        "- update_hubspot_marketing_email(email_id: string, updates_json: string) -> {status} (requires OAuth)\n"
        "\n"
        "## Codex Workspace Tools\n"
        "- codex.run(instruction: string, model?: string, timeout_seconds?: int) -> {text, artifacts, output_policy} (high-level, requires OpenAI)\n"
        "- codex.create_workspace(name_hint: string, keep?: bool) -> {workspace_id}\n"
        "- codex.start_codex_run(workspace_id: string, instruction: string) -> {run_id}\n"
        "- codex.get_codex_run(run_id: string) -> {status, summary, artifacts}\n"
        "- codex.read_file(workspace_id: string, relative_path: string) -> text\n"
        "- codex.get_manifest(workspace_id: string) -> {files, metadata}\n"
        "- codex.cleanup_workspace(workspace_id: string) -> {status}\n"
        "\n"
        "## LLM-only Tools\n"
        "- llm.generate(prompt?: string) -> text (runs local LLM; if prompt omitted, uses step instruction)\n"
    )


def build_planning_prompt(goal: str, allowed_tools: List[str], budget: Dict | None, planner_hints: Dict | None = None) -> str:
    schema = {
        "type": "object",
        "required": ["constraints", "resources", "steps"],
        "properties": {
            "constraints": {"type": "array", "items": {"type": "string"}},
            "resources": {"type": "array", "items": {"type": "string"}},
            "steps": {
                "type": "array",
                "minItems": 3,
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "required": ["id", "title", "instruction", "tool", "success_criteria"],
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "instruction": {"type": "string"},
                        "tool": {"type": "string", "enum": allowed_tools},
                        "params": {"type": "object"},
                        "success_criteria": {"type": "string"},
                        "max_retries": {"type": "integer", "minimum": 0, "default": 1}
                    }
                }
            }
        }
    }
    hints = planner_hints or {}
    manifest = hints.get("manifest") if isinstance(hints, dict) else None
    step_hint = hints.get("step_plan") if isinstance(hints, dict) else None
    manifest_text = ("\nPlanner manifest (use identifiers exactly; do not invent new ones):\n" + json.dumps(manifest)) if manifest else ""
    step_hint_text = ("\nSuggested step skeleton (align your plan to this, but keep within allowed tools):\n" + json.dumps(step_hint)) if step_hint else ""
    return (
        "You are a planning agent. Generate a plan as strict JSON only.\n"
        f"Goal: {goal}\n"
        f"Allowed tools: {allowed_tools}\n"
        f"Tool catalog:\n{_tool_catalog_text()}\n"
        f"Budget: {budget or {}}\n"
        f"{manifest_text}"
        f"{step_hint_text}"
        "Constraints: Use only allowed tools; be concise; 3-10 steps; each step has id,title,instruction,tool,params?,success_criteria,max_retries.\n"
        "Important: Only use python.* tools if the user provides a CSV (python.load_csv must appear before any other python.* tool).\n"
        "Important: HubSpot tools require OAuth authentication - they will fail if not configured.\n"
        "Important: Codex tools require OpenAI API key - use llm.generate as fallback if unavailable.\n"
        "Do NOT fabricate dataframe IDs; do not reference 'result of step X' as a dataframe id. When analyzing web_search output, use llm.generate to extract or write content.\n"
        "For web searches, prefer smart_search_extract over web_search for better content extraction.\n"
        f"JSON schema (for guidance): {json.dumps(schema)}\n"
        "Output ONLY the JSON object. No prose."
    )


async def plan_task(goal: str, model: str | None, budget: Dict | None, planner_hints: Dict | None = None) -> Plan:
    model_name = model or await get_default_ollama_model()
    if not model_name or model_name.strip() == "":
        model_name = "llama3.1"  # Hard fallback
        logger.warning(f"Using hard fallback model: {model_name}")
    prompt = build_planning_prompt(goal, ALLOWED_TASK_TOOLS, budget, planner_hints)
    raw = await chat_with_provider([
        {"role": "system", "content": "You produce only JSON."},
        {"role": "user", "content": prompt},
    ], model_name)
    if not raw:
        # Fallback minimal plan
        logger.warning("Planner received no content; returning minimal plan.")
        return Plan(constraints=[], resources=[], steps=[
            PlanStep(id="s1", title="Search web", instruction=goal, tool="web_search", params={"query": goal}, success_criteria="Found at least one relevant result")
        ])
    plan_dict = None
    try:
        plan_dict = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Planner returned invalid JSON; attempting repair.")
        # Very naive repair: extract first {...}
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                plan_dict = json.loads(raw[start:end+1])
            except Exception:
                pass
    if not plan_dict:
        logger.error("Planner failed to provide JSON; returning minimal plan.")
        return Plan(constraints=[], resources=[], steps=[
            PlanStep(id="s1", title="Search web", instruction=goal, tool="web_search", params={"query": goal}, success_criteria="Found at least one relevant result")
        ])

    # Enforce tool whitelist and coerce steps
    steps = []
    for i, st in enumerate(plan_dict.get("steps", [])):
        tool = _normalize_tool(st.get("tool"))
        if tool not in ALLOWED_TASK_TOOLS:
            logger.warning(f"Planner proposed tool not allowed: {st.get('tool')}; skipping step {i}")
            continue
        steps.append(PlanStep(
            id=str(st.get("id", f"s{i+1}")),
            title=st.get("title", f"Step {i+1}"),
            instruction=st.get("instruction", ""),
            tool=tool,
            params=st.get("params") or {},
            success_criteria=st.get("success_criteria", "Executed without error"),
            max_retries=int(st.get("max_retries", 1)),
        ))
    if not steps:
        steps = [PlanStep(id="s1", title="Search web", instruction=goal, tool="web_search", params={"query": goal}, success_criteria="Found at least one relevant result")]
    # Ensure there's a generative step when appropriate
    have_generate = any(s.tool == "llm.generate" for s in steps)
    if not have_generate:
        # Heuristic: if goal implies writing or we only have a single step, add a generate step
        gl = (goal or "").lower()
        wants_writing = any(w in gl for w in ["write", "email", "newsletter", "summary", "report", "compose", "draft"]) or len(steps) < 2
        if wants_writing:
            steps.append(PlanStep(
                id=f"s{len(steps)+1}",
                title="Generate final output",
                instruction="Using the outputs of prior steps, produce the requested deliverable.",
                tool="llm.generate",
                params={},
                success_criteria="Output fulfills the user's request succinctly",
                max_retries=1,
            ))
    plan = Plan(
        constraints=plan_dict.get("constraints", []),
        resources=plan_dict.get("resources", []),
        steps=steps,
    )
    # Sanitize plan: avoid python dataframe tools unless a CSV is loaded earlier
    try:
        has_csv_load = any(s.tool == "python.load_csv" for s in plan.steps)
        if not has_csv_load:
            fixed_steps: List[PlanStep] = []
            for s in plan.steps:
                if s.tool and s.tool.startswith("python.") and s.tool != "python.load_csv":
                    # Replace with a generate step to extract/transform text instead of DataFrame ops
                    fixed_steps.append(PlanStep(
                        id=s.id,
                        title=(s.title or "Generate output"),
                        instruction=(s.instruction or "Summarize and extract key points from prior step outputs."),
                        tool="llm.generate",
                        params={},
                        success_criteria="Text captures key facts succinctly",
                        max_retries=s.max_retries or 1,
                    ))
                else:
                    fixed_steps.append(s)
            plan.steps = fixed_steps
    except Exception:
        pass

    # Gate Codex (requires OpenAI key)
    try:
        from services.provider_service import get_provider_status
        status = await get_provider_status('openai')
        if not status.get('configured'):
            gated: List[PlanStep] = []
            for s in plan.steps:
                if s.tool == "codex.run":
                    gated.append(PlanStep(
                        id=s.id,
                        title=s.title or "Generate output",
                        instruction=s.instruction or "Write a concise result based on context.",
                        tool="llm.generate",
                        params={},
                        success_criteria=s.success_criteria or "Produced a useful result",
                        max_retries=s.max_retries or 1,
                    ))
                else:
                    gated.append(s)
            plan.steps = gated
    except Exception:
        pass

    # Heuristic: add Codex step for code scaffolding goals if available
    try:
        from services.provider_service import get_provider_status
        status = await get_provider_status('openai')
        codex_ok = bool(status.get('configured'))
        keywords = ["scaffold", "generate code", "build app", "web app", "init repo", "create files", "project structure"]
        if codex_ok and not any(s.tool == "codex.run" for s in plan.steps):
            gl = (goal or "").lower()
            if any(k in gl for k in keywords):
                plan.steps.append(PlanStep(
                    id=f"s{len(plan.steps)+1}",
                    title="Run Codex to generate workspace",
                    instruction=goal,
                    tool="codex.run",
                    params={},
                    success_criteria="Workspace generated with relevant files",
                    max_retries=0,
                ))
    except Exception:
        pass

    return plan
