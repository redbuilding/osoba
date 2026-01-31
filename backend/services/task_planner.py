import json
from typing import Dict, List

from core.config import get_logger
from core.models import Plan, PlanStep
from services.provider_service import chat_with_provider
from services.llm_service import get_default_ollama_model


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
    "codex.run",
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
    # search variants
    "search": "web_search",
    "web-search": "web_search",
    "google_search": "web_search",
    "bing_search": "web_search",
    # generation variants
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
        "Important: Only use python.* tools if the user provides a CSV (python.load_csv must appear before any python.query_dataframe).\n"
        "Do NOT fabricate dataframe IDs; do not reference 'result of step X' as a dataframe id. When analyzing web_search output, use llm.generate to extract or write content.\n"
        f"JSON schema (for guidance): {json.dumps(schema)}\n"
        "Output ONLY the JSON object. No prose."
    )


async def plan_task(goal: str, model: str | None, budget: Dict | None) -> Plan:
    model_name = model or await get_default_ollama_model()
    if not model_name or model_name.strip() == "":
        model_name = "llama3.1"  # Hard fallback
        logger.warning(f"Using hard fallback model: {model_name}")
    prompt = build_planning_prompt(goal, ALLOWED_TASK_TOOLS, budget)
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
