import json
from typing import Dict, List

from core.config import get_logger
from core.models import Plan, PlanStep
from services.ollama_service import chat_with_ollama, get_default_ollama_model


logger = get_logger("task_planner")

ALLOWED_TASK_TOOLS = [
    "web_search",
    "execute_sql_query_tool",
    "get_youtube_transcript",
    "python.load_csv",
    "python.get_head",
    "python.get_descriptive_statistics",
    "python.create_plot",
    "python.query_dataframe",
    "llm.generate",
]


def _tool_catalog_text() -> str:
    return (
        "- web_search(query: string) -> {status, organic_results...}\n"
        "- execute_sql_query_tool(query: string) -> {columns, rows} (read-only)\n"
        "- get_youtube_transcript(youtube_url: string) -> text\n"
        "- python.load_csv(csv_b64: string) -> text (includes dataframe ID)\n"
        "- python.get_head(df_id: string, n?: int) -> text\n"
        "- python.get_descriptive_statistics(df_id: string) -> text\n"
        "- python.create_plot(df_id: string, plot_type: string, x_col: string, y_col?: string) -> image b64\n"
        "- python.query_dataframe(df_id: string, query_string: string) -> text (may include new df id)\n"
        "- llm.generate(prompt?: string) -> text (runs local LLM; if prompt omitted, uses step instruction)\n"
    )


def build_planning_prompt(goal: str, allowed_tools: List[str], budget: Dict | None) -> str:
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
    return (
        "You are a planning agent. Generate a plan as strict JSON only.\n"
        f"Goal: {goal}\n"
        f"Allowed tools: {allowed_tools}\n"
        f"Tool catalog:\n{_tool_catalog_text()}\n"
        f"Budget: {budget or {}}\n"
        "Constraints: Use only allowed tools; be concise; 3-10 steps; each step has id,title,instruction,tool,params?,success_criteria,max_retries.\n"
        f"JSON schema (for guidance): {json.dumps(schema)}\n"
        "Output ONLY the JSON object. No prose."
    )


async def plan_task(goal: str, model: str | None, budget: Dict | None) -> Plan:
    model_name = model or await get_default_ollama_model()
    if not model_name or model_name.strip() == "":
        model_name = "llama3.1"  # Hard fallback
        logger.warning(f"Using hard fallback model: {model_name}")
    prompt = build_planning_prompt(goal, ALLOWED_TASK_TOOLS, budget)
    raw = await chat_with_ollama([
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
        tool = st.get("tool")
        if tool not in ALLOWED_TASK_TOOLS:
            logger.warning(f"Planner proposed tool not allowed: {tool}; skipping step {i}")
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
    plan = Plan(
        constraints=plan_dict.get("constraints", []),
        resources=plan_dict.get("resources", []),
        steps=steps,
    )
    return plan
