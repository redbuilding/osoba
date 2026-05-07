import json
from typing import Dict, List, Optional, Set

from core.config import (
    CANVA_SERVICE_NAME,
    CLI_SERVICE_NAME,
    CODEX_SERVICE_NAME,
    FIGMA_SERVICE_NAME,
    HUBSPOT_SERVICE_NAME,
    MYSQL_DB_SERVICE_NAME,
    POE_SERVICE_NAME,
    PYTHON_SERVICE_NAME,
    WEB_SEARCH_SERVICE_NAME,
    YOUTUBE_SERVICE_NAME,
    get_logger,
)
from core.models import Plan, PlanStep
from services.provider_service import chat_with_provider
from services.llm_service import get_default_ollama_model


logger = get_logger("task_planner")

ALLOWED_TASK_TOOLS = [
    # Web Search MCP (5 tools)
    "web_search",                    # Basic search
    "smart_search_extract",          # Smart extraction (chat uses this by default!)
    "image_search",                  # Image-specific search
    "news_search",                   # News-specific search
    "fetch_url",                     # Fetch content from a specific URL
    
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
    
    # Canva Design MCP (10 tools)
    "create_design",                 # Create a new Canva design
    "list_designs",                  # List designs in account
    "get_design",                    # Get a specific design by ID
    "export_design",                 # Export design to PNG/JPG/PDF/etc.
    "upload_asset",                  # Upload image/video to Canva library
    "autofill_design",               # Autofill a brand template with data
    "get_brand_template_dataset",    # Get autofillable fields from a template
    "import_design",                 # Import PDF/PPTX/DOCX/PSD into Canva
    "resize_design",                 # Create a resized copy of a design
    "get_design_pages",              # Get page metadata for a design

    # Figma Design MCP (6 tools)
    "figma_get_file",                # Get Figma file structure and metadata
    "figma_get_nodes",               # Get specific nodes by ID
    "figma_export_images",           # Export nodes as PNG/JPG/SVG/PDF images
    "figma_get_comments",            # List comments on a file
    "figma_post_comment",            # Post a comment to a file
    "figma_get_design_system",       # Extract design tokens and components

    # Poe AI Platform MCP (5 tools)
    "poe_list_models",               # List available Poe models by modality
    "poe_chat",                      # Text chat with any Poe model
    "poe_generate_image",            # Image generation via Poe image models
    "poe_generate_video",            # Video generation via Poe video models
    "poe_generate_audio",            # Audio generation via Poe audio models

    # CLI System Tools MCP (5 tools)
    "cli.get_system_health",         # Disk, uptime, platform — no args
    "cli.list_dir",                  # List artifacts, logs, or scripts directory
    "cli.read_log",                  # Read tail of a named log file
    "cli.service_status",            # systemd service status (allowlisted services)
    "cli.read_workspace_file",       # Read a file from the artifacts directory

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

    # Fetch URL variants
    "fetch": "fetch_url",
    "get_url": "fetch_url",
    "scrape_url": "fetch_url",
    "read_url": "fetch_url",
    
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
    
    # Canva design variants
    "canva_create": "create_design",
    "design": "create_design",
    "new_design": "create_design",
    "canva_list": "list_designs",
    "canva_get": "get_design",
    "canva_export": "export_design",
    "export": "export_design",
    "canva_upload": "upload_asset",
    "canva_autofill": "autofill_design",
    "canva_template_fields": "get_brand_template_dataset",
    "canva_import": "import_design",
    "canva_resize": "resize_design",
    "canva_pages": "get_design_pages",

    # Figma design variants
    "figma_file": "figma_get_file",
    "figma_nodes": "figma_get_nodes",
    "figma_images": "figma_export_images",
    "figma_comments": "figma_get_comments",
    "figma_comment": "figma_post_comment",
    "figma_design_system": "figma_get_design_system",
    "figma_tokens": "figma_get_design_system",

    # CLI system tool variants
    "cli.system_health": "cli.get_system_health",
    "cli.health": "cli.get_system_health",
    "cli.disk": "cli.get_system_health",
    "cli.ls": "cli.list_dir",
    "cli.list": "cli.list_dir",
    "cli.tail": "cli.read_log",
    "cli.log": "cli.read_log",
    "cli.logs": "cli.read_log",
    "cli.status": "cli.service_status",
    "cli.read_file": "cli.read_workspace_file",
    "cli.read": "cli.read_workspace_file",

    # Poe platform variants
    "poe_models": "poe_list_models",
    "poe_image": "poe_generate_image",
    "poe_video": "poe_generate_video",
    "poe_audio": "poe_generate_audio",
    "poe": "poe_chat",
    "poe_generate": "poe_chat",

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


_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "web":      ["search", "research", "find", "look up", "article", "news", "website", "url", "web", "fetch", "browse"],
    "data":     ["csv", "data", "analyz", "statistic", "correlation", "plot", "chart", "dataframe", "outlier", "hypothesis", "dataset"],
    "canva":    ["canva", "design", "template", "brand", "poster", "social media", "instagram", "facebook", "linkedin", "thumbnail"],
    "figma":    ["figma", "component", "design system", "token", "wireframe", "ui design", "mockup"],
    "poe":      ["image", "picture", "photo", "illustrat", "draw", "artwork", "video", "audio", "sound", "music", "poe", "generate image", "generate video"],
    "database": ["database", "sql", "query", "table", "mysql", "db"],
    "codex":    ["code", "scaffold", "build app", "web app", "script", "function", "program", "codex", "repository", "init repo"],
    "youtube":  ["youtube", "transcript", "video transcript"],
    "hubspot":  ["email", "hubspot", "marketing", "newsletter", "campaign"],
    "cli":      ["system", "disk", "log", "service", "health", "uptime", "cli", "server status"],
}

_SERVICE_TOOL_GROUPS: Dict[str, List[str]] = {
    WEB_SEARCH_SERVICE_NAME: ["web_search", "smart_search_extract", "image_search", "news_search", "fetch_url"],
    MYSQL_DB_SERVICE_NAME:   ["execute_sql_query_tool"],
    YOUTUBE_SERVICE_NAME:    ["get_youtube_transcript"],
    HUBSPOT_SERVICE_NAME:    ["create_hubspot_marketing_email", "update_hubspot_marketing_email"],
    PYTHON_SERVICE_NAME:     [t for t in ALLOWED_TASK_TOOLS if t.startswith("python.")],
    CODEX_SERVICE_NAME:      [t for t in ALLOWED_TASK_TOOLS if t.startswith("codex.")],
    CANVA_SERVICE_NAME:      ["create_design", "list_designs", "get_design", "export_design",
                               "upload_asset", "autofill_design", "get_brand_template_dataset",
                               "import_design", "resize_design", "get_design_pages"],
    FIGMA_SERVICE_NAME:      ["figma_get_file", "figma_get_nodes", "figma_export_images",
                               "figma_get_comments", "figma_post_comment", "figma_get_design_system"],
    POE_SERVICE_NAME:        ["poe_list_models", "poe_chat", "poe_generate_image",
                               "poe_generate_video", "poe_generate_audio"],
    CLI_SERVICE_NAME:        ["cli.get_system_health", "cli.list_dir", "cli.read_log",
                               "cli.service_status", "cli.read_workspace_file"],
}


def _classify_goal_intent(goal: str) -> Set[str]:
    """Return tool categories relevant to a goal. Always includes 'llm'. Defaults to web+llm."""
    gl = goal.lower()
    categories: Set[str] = {"llm"}
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in gl for kw in keywords):
            categories.add(category)
    if categories == {"llm"}:
        categories.add("web")
    return categories


def get_enabled_tools(mcp_app_state=None) -> List[str]:
    """Return the subset of ALLOWED_TASK_TOOLS whose backing MCP service is currently enabled."""
    try:
        from services.mcp_service import app_state as _app_state
        state = mcp_app_state or _app_state
        enabled: Set[str] = {"llm.generate"}
        for service, tools in _SERVICE_TOOL_GROUPS.items():
            cfg = state.mcp_configs.get(service)
            if cfg and cfg.enabled:
                enabled.update(tools)
        return [t for t in ALLOWED_TASK_TOOLS if t in enabled]
    except Exception:
        return list(ALLOWED_TASK_TOOLS)


def _tool_catalog_text(categories: Optional[Set[str]] = None) -> str:
    _CATALOG_SECTIONS: Dict[str, str] = {
        "web": (
            "## Web Search Tools\n"
            "- web_search(query: string) -> {status, organic_results...}\n"
            "- smart_search_extract(query: string, max_urls?: int, max_chars_per_url?: int) -> {extracted_content, search_summary}\n"
            "- image_search(query: string) -> {status, images...}\n"
            "- news_search(query: string) -> {status, news_results...}\n"
            "- fetch_url(url: string, max_chars?: int) -> {status, content, title, url} (fetch content from a known URL)\n"
        ),
        "database": (
            "## Database Tools\n"
            "- execute_sql_query_tool(query: string) -> {columns, rows} (read-only SELECT only)\n"
        ),
        "youtube": (
            "## YouTube Tools\n"
            "- get_youtube_transcript(youtube_url: string) -> text\n"
        ),
        "data": (
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
        ),
        "hubspot": (
            "## HubSpot Business Tools\n"
            "- create_hubspot_marketing_email(email_json: string) -> {status, email_id} (requires OAuth)\n"
            "- update_hubspot_marketing_email(email_id: string, updates_json: string) -> {status} (requires OAuth)\n"
        ),
        "codex": (
            "## Codex Workspace Tools\n"
            "- codex.run(instruction: string, model?: string, timeout_seconds?: int) -> {text, artifacts, output_policy} (high-level, requires OpenAI)\n"
            "- codex.create_workspace(name_hint: string, keep?: bool) -> {workspace_id}\n"
            "- codex.start_codex_run(workspace_id: string, instruction: string) -> {run_id}\n"
            "- codex.get_codex_run(run_id: string) -> {status, summary, artifacts}\n"
            "- codex.read_file(workspace_id: string, relative_path: string) -> text\n"
            "- codex.get_manifest(workspace_id: string) -> {files, metadata}\n"
            "- codex.cleanup_workspace(workspace_id: string) -> {status}\n"
        ),
        "canva": (
            "## Canva Design Tools\n"
            "- create_design(title: string, preset?: string, width?: int, height?: int, unit?: string, template_id?: string) -> {status, id, url, thumbnail_url}\n"
            "  presets: instagram_post, instagram_story, facebook_post, facebook_cover, twitter_post, linkedin_banner, youtube_thumbnail, presentation, a4, a3, us_letter, custom\n"
            "- list_designs(page_token?: string, limit?: int) -> {status, items, next_page_token}\n"
            "- get_design(design_id: string) -> {status, id, title, url, thumbnail_url, width, height}\n"
            "- export_design(design_id: string, format?: string, width?: int, height?: int, quality?: int, pages?: string) -> {status, download_url, job_id}\n"
            "  formats: png, jpg, pdf, svg, mp4, gif\n"
            "- upload_asset(name: string, url: string) -> {status, asset_id, name, type}\n"
            "- autofill_design(brand_template_id: string, data: string, title?: string) -> {status, design_id, url}\n"
            "  data is a JSON string of field values; use get_brand_template_dataset first to discover fields\n"
            "- get_brand_template_dataset(brand_template_id: string) -> {status, dataset}\n"
            "- import_design(title: string, url: string, mime_type?: string) -> {status, designs}\n"
            "  imports PDF, PPTX, DOCX, PSD, AI, Keynote etc. from a public URL into Canva as editable designs\n"
            "- resize_design(design_id: string, width: int, height: int) -> {status, design_id, url}\n"
            "- get_design_pages(design_id: string) -> {status, pages}\n"
        ),
        "figma": (
            "## Figma Design Tools\n"
            "- figma_get_file(file_key: string, depth?: int) -> {status, name, lastModified, version, document, components, styles}\n"
            "  file_key is found in the Figma URL: figma.com/file/{file_key}/...\n"
            "- figma_get_nodes(file_key: string, node_ids: string, depth?: int) -> {status, name, nodes}\n"
            "  node_ids: comma-separated IDs e.g. '1:2,3:4'\n"
            "- figma_export_images(file_key: string, node_ids: string, format?: string, scale?: float) -> {status, images}\n"
            "  formats: png, jpg, svg, pdf — returns map of node_id -> download URL\n"
            "- figma_get_comments(file_key: string) -> {status, comments}\n"
            "- figma_post_comment(file_key: string, message: string, node_id?: string, parent_id?: string) -> {status, id, message}\n"
            "- figma_get_design_system(file_key: string) -> {status, colors, typography, spacing, effects, components}\n"
        ),
        "poe": (
            "## Poe AI Platform Tools\n"
            "- poe_list_models(input_modality?: string, output_modality?: string, search?: string, limit?: int) -> {status, count, models}\n"
            "  modalities: text, image, video, audio\n"
            "- poe_chat(prompt: string, model?: string, system?: string, temperature?: float, max_tokens?: int, image_urls?: list) -> {status, model, text}\n"
            "  default model: Claude-Sonnet-4-6\n"
            "- poe_generate_image(prompt: string, model?: string, system?: string, aspect_ratio?: string, download_media?: bool) -> {status, model, raw_text, extracted_urls, downloaded}\n"
            "  default model: gpt-image-1.5; aspect_ratio: '9:16' (portrait) or '16:9' (landscape); downloaded items contain data_b64 for inline delivery\n"
            "- poe_generate_video(prompt: string, model: string, system?: string, download_media?: bool) -> {status, model, raw_text, extracted_urls, downloaded}\n"
            "  model required — use poe_list_models(output_modality='video') to find one\n"
            "- poe_generate_audio(prompt: string, model: string, system?: string, download_media?: bool) -> {status, model, raw_text, extracted_urls, downloaded}\n"
            "  model required — use poe_list_models(output_modality='audio') to find one\n"
        ),
        "cli": (
            "## CLI System Tools\n"
            "- cli.get_system_health() -> {platform, node, release, disk, uptime} (no args; safe system snapshot)\n"
            "- cli.list_dir(scope: 'artifacts'|'logs'|'scripts') -> {scope, entry_count, entries} (list allowed dirs only)\n"
            "- cli.read_log(name: string, lines?: int) -> {name, lines_returned, total_lines, content} (tail of a log file; name must be exact filename e.g. 'mcp_backend.log')\n"
            "- cli.service_status(name: string) -> {service, status, active_state, sub_state, description} (requires service in CLI_ALLOWED_SERVICES)\n"
            "- cli.read_workspace_file(path_within_scope: string) -> {path, size_bytes, content, truncated} (read file from artifacts dir; relative path only)\n"
        ),
        "llm": (
            "## LLM-only Tools\n"
            "- llm.generate(prompt?: string) -> text (runs local LLM; if prompt omitted, uses step instruction)\n"
        ),
    }
    if categories is None:
        return "\n".join(_CATALOG_SECTIONS.values())
    return "\n".join(v for k, v in _CATALOG_SECTIONS.items() if k in categories)


def build_planning_prompt(goal: str, allowed_tools: List[str], budget: Dict | None, planner_hints: Dict | None = None, kb_context: str = "") -> str:
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
    kb_text = f"\nReference material (use this to inform your plan):\n{kb_context}\n" if kb_context else ""
    goal_categories = _classify_goal_intent(goal)
    filtered_catalog = _tool_catalog_text(goal_categories)
    return (
        "You are a planning agent. Generate a plan as strict JSON only.\n"
        f"Goal: {goal}\n"
        f"Allowed tools: {allowed_tools}\n"
        f"Tool catalog:\n{filtered_catalog}\n"
        f"Budget: {budget or {}}\n"
        f"{manifest_text}"
        f"{step_hint_text}"
        f"{kb_text}"
        "Constraints: Use only allowed tools; be concise; 3-10 steps; each step has id,title,instruction,tool,params?,success_criteria,max_retries.\n"
        "Important: Only use python.* tools if the user provides a CSV (python.load_csv must appear before any other python.* tool).\n"
        "Important: HubSpot tools require OAuth authentication - they will fail if not configured.\n"
        "Important: Codex tools require OpenAI API key - use llm.generate as fallback if unavailable.\n"
        "Do NOT fabricate dataframe IDs; do not reference 'result of step X' as a dataframe id. When analyzing web_search output, use llm.generate to extract or write content.\n"
        "For web searches, prefer smart_search_extract over web_search for better content extraction.\n"
        f"JSON schema (for guidance): {json.dumps(schema)}\n"
        "Output ONLY the JSON object. No prose."
    )


async def plan_task(goal: str, model: str | None, budget: Dict | None, planner_hints: Dict | None = None, kb_context: str = "", enabled_tools: Optional[List[str]] = None) -> Plan:
    model_name = model or await get_default_ollama_model()
    if not model_name or model_name.strip() == "":
        model_name = "llama3.1"  # Hard fallback
        logger.warning(f"Using hard fallback model: {model_name}")
    tools = enabled_tools if enabled_tools is not None else ALLOWED_TASK_TOOLS
    prompt = build_planning_prompt(goal, tools, budget, planner_hints, kb_context)
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
    return Plan(
        constraints=plan_dict.get("constraints", []),
        resources=plan_dict.get("resources", []),
        steps=steps,
    )
