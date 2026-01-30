# Long-Running Tasks: Plan-and-Execute Feature

This document provides an implementation plan to add autonomous, long-running task execution to the app. It is designed to be followed end-to-end by a developer, integrating with the existing Ollama + MCP architecture.

## Objectives

- Enable users to submit high-level goals that the app plans and executes over time without user supervision.
- Provide a durable task state machine (planning → running → completed/failed) that survives restarts.
- Stream progress (SSE) to the UI and persist step logs and artifacts.
- Reuse existing MCP tools (web search, SQL, YouTube, Python) and Ollama for planning and verification.
- Offer controls: pause, resume, cancel, and budgets (time/tool calls).

## Non-Goals (Initial Release)

- Arbitrary filesystem/network mutations beyond existing MCP tools.
- Multi-node distributed scheduling. (Optional future.)
- Complex human-in-the-loop review gates. (Add later if needed.)

---

## High-Level Architecture

- Planner (LLM): Produces a structured, executable plan (strict JSON schema) from a user goal.
- Runner: Background worker that executes plan steps, calls MCP tools, verifies success, retries, and records outputs.
- Persistence (MongoDB): `tasks` collection for task/plan/state; logs and artifacts embedded or separate collection.
- API: Create/manage tasks, stream progress, and query state.
- Frontend: “Tasks” panel to create, monitor, and control long-running tasks with live updates.

---

## Data Model (MongoDB)

Add a new collection `tasks` with the following document shape and indexes.

- Collection: `tasks`
  - Fields:
    - `_id`: ObjectId
    - `title`: string (default: derived from goal)
    - `goal`: string (user input)
    - `status`: enum [PLANNING, PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELED]
    - `created_at`: datetime (UTC)
    - `updated_at`: datetime (UTC)
    - `conversation_id`: string | null (optional association to a chat)
    - `ollama_model_name`: string (the model used for planning/reasoning)
    - `budget`: object { `max_seconds`: int, `max_tool_calls`: int }
    - `usage`: object { `tool_calls`: int, `seconds_elapsed`: int }
    - `plan`: object
      - `constraints`: string[]
      - `resources`: string[]
      - `steps`: Step[] (see below)
    - `current_step_index`: int (0-based, -1 before running)
    - `summary`: string | null (final result summary)
    - `error`: string | null (top-level error on failure)
  - Indexes:
    - `status` (for polling/dispatch)
    - `updated_at` (descending)

- Step structure (embedded inside `plan.steps`):
  - `id`: string
  - `title`: string
  - `instruction`: string (natural language instruction)
  - `tool`: enum [web_search, execute_sql_query_tool, get_youtube_transcript, python.load_csv, python.get_head, python.get_descriptive_statistics, python.create_plot, python.query_dataframe, ...] (only existing tools initially)
  - `params`: object (tool-specific input; may contain templates like "{{prev.outputs.key}}")
  - `success_criteria`: string (how we judge success; brief and concrete)
  - `max_retries`: int (default 1–2)
  - `status`: enum [PENDING, RUNNING, COMPLETED, FAILED, SKIPPED]
  - `retries`: int
  - `outputs`: object (normalized results; may include text and `artifacts` array)
  - `error`: string | null
  - `started_at`, `ended_at`: datetime

- Optional: `task_events` collection (if logs become large)
  - Fields: `task_id`, `ts`, `type` (INFO|WARN|ERROR|STEP_START|STEP_END|ARTIFACT), `payload`
  - Index on `task_id`, `ts`.

Migration/setup:
- Create collection lazily; no data migration required. Consider creating indexes on first use.

---

## Backend Changes

### 1) New Pydantic Models (backend/core/models.py)

Add new models for API I/O explicitly (do not tie API payloads to DB shapes 1:1):
- `TaskCreatePayload { goal: str, conversation_id?: str, ollama_model_name?: str, budget?: { max_seconds?: int, max_tool_calls?: int }, dry_run?: bool }`
- `TaskSummary { id: str, title: str, goal: str, status: str, created_at: datetime, updated_at: datetime }`
- `TaskDetail { ...all top-level task fields..., plan: Plan, current_step_index: int }`
- `Plan { constraints: List[str], resources: List[str], steps: List[PlanStep] }`
- `PlanStep { id: str, title: str, instruction: str, tool: str, params: Dict[str, Any] | None, success_criteria: str, max_retries: int, status: str, retries: int, outputs: Dict[str, Any] | None, error: str | None, started_at: datetime | None, ended_at: datetime | None }`

Implementation notes:
- Provide `json_encoders` for datetimes.
- Validate `tool` against a whitelist; reject unknown tools.

### 2) CRUD Layer (backend/db/tasks_crud.py)

Implement helpers to encapsulate DB access:
- `create_task(doc: Dict) -> str`
- `get_task(task_id: str) -> Dict | None`
- `list_tasks(limit=50) -> List[Dict]`
- `update_task(task_id: str, patch: Dict) -> None`
- `append_event(task_id: str, event: Dict) -> None` (if using `task_events`)
- `set_step_status(task_id: str, idx: int, patch: Dict) -> None`
- `increment_usage(task_id: str, field: str, delta: int) -> None`
- `create_indexes()`: ensure indexes (`status`, `updated_at`).

### 3) Planner (backend/services/task_planner.py)

Responsibilities:
- Build a strict planning prompt with JSON schema.
- Call `ollama_service.chat_with_ollama` to generate a plan.
- Validate and, if needed, run a repair pass if JSON invalid.
- Return a validated `Plan` object.

Key functions:
- `build_planning_prompt(goal: str, allowed_tools: List[str], budget: Dict) -> str`
- `plan_task(goal: str, model: str, budget: Dict) -> Plan`
- `validate_plan(plan: Dict) -> Plan` (Pydantic validation + tool whitelist check)

JSON schema (high-level):
```json
{
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
          "tool": {"type": "string", "enum": ["web_search", "execute_sql_query_tool", "get_youtube_transcript", "python.load_csv", "python.get_head", "python.get_descriptive_statistics", "python.create_plot", "python.query_dataframe"]},
          "params": {"type": "object"},
          "success_criteria": {"type": "string"},
          "max_retries": {"type": "integer", "minimum": 0, "default": 1}
        }
      }
    }
  }
}
```

Prompt outline (pseudo):
- System: constraints, tool catalog with exact names and param shapes, safety rules (no filesystem/network outside tools).
- User: the `goal`, optional context (conversation summary), budget.
- Assistant: “Return only JSON that matches the schema exactly. No prose.”

### 4) Runner (backend/services/task_runner.py)

Responsibilities:
- Background task dispatcher that watches for tasks to execute.
- Execute steps sequentially with retry and success evaluation.
- Update DB state and publish SSE events.

Initialization:
- `start_task_dispatcher(app_state)`: called from FastAPI lifespan.
- On startup, transition orphaned RUNNING → PAUSED; PLANNING without plan → FAILED (or re-plan).

Core functions:
- `dispatch_loop(stop_event)`:
  - Periodically: fetch tasks with status in {PENDING, RUNNING}.
  - For `PENDING`: set `RUNNING`, `current_step_index = 0` and spawn `run_task(task_id)`.
  - For `RUNNING` without an active worker (crash recovery): spawn worker.
- `run_task(task_id)`: state machine
  - Load task; enforce budget/timeouts.
  - For idx in steps: if PAUSED/CANCELED, break; else `execute_step(task, idx)`; store outputs; advance index.
  - On success: set COMPLETED + summary (from last step or LLM summarizer).
  - On failure: set FAILED + error.
- `execute_step(task, idx)`: 
  - Resolve param templates using previous outputs (simple `{{prev.X}}` or `{{steps['id'].outputs.key}}`).
  - Select tool → MCP mapping; call via `submit_mcp_request` / `wait_mcp_response` with appropriate `service_name` and `tool`.
  - Normalize result to `{ text?: str, rows?: [...], image_b64?: string, artifacts?: [...] }`.
  - Evaluate success: `evaluate_success(plan_step, normalized_result)`.
  - On failure: retry up to `max_retries` with backoff; optionally call `revise_step_with_llm(previous_error)` (phase 2).
- `evaluate_success(step, result)`: 
  - If `success_criteria` trivial, use rule-based check.
  - Else call `ollama_service.chat_with_ollama` with a verification prompt that outputs `true|false` and a one-sentence reason.

Budgets/Timeouts:
- Per-step timeout (e.g., 120s default) and per-task max wall time (`budget.max_seconds`).
- Track `usage.tool_calls` and abort if exceeded.

Events:
- Emit SSE events for: TASK_STATUS, STEP_STATUS, STEP_LOG, ARTIFACT, SUMMARY.

### 5) Progress Bus (backend/services/progress_bus.py)

Provide a per-task pub/sub for SSE without external brokers.
- In-memory `asyncio.Queue` per `task_id`.
- `subscribe(task_id) -> AsyncGenerator[str]` yields `data: {json}\n\n` lines.
- Runner pushes events; API streams to client.
- On server restart, new subscribers only get new events; client should refresh state via GET detail.

Event payloads (examples):
```json
{ "type": "TASK_STATUS", "task_id": "...", "status": "RUNNING" }
{ "type": "STEP_STATUS", "task_id": "...", "index": 2, "status": "COMPLETED" }
{ "type": "STEP_LOG", "task_id": "...", "index": 1, "level": "INFO", "message": "Called web_search ..." }
{ "type": "ARTIFACT", "task_id": "...", "index": 3, "mime": "image/png", "data": "<base64>" }
{ "type": "SUMMARY", "task_id": "...", "text": "..." }
```

### 6) Tool Invocation Mapping

Create a small resolver in `task_runner.py`:
- `resolve_tool(tool: str) -> (service_name: str, tool_name: str)`
  - `web_search` → (`WEB_SEARCH_SERVICE_NAME`, `web_search`)
  - `execute_sql_query_tool` → (`MYSQL_DB_SERVICE_NAME`, `execute_sql_query_tool`)
  - `get_youtube_transcript` → (`YOUTUBE_SERVICE_NAME`, `get_youtube_transcript`)
  - `python.<x>` → (`PYTHON_SERVICE_NAME`, `<x>`) e.g., `python.create_plot` → `create_plot` with params map

Parameters:
- Define param schemas in the planner prompt; validate in runner before call; coerce to the expected shape.

### 7) API (backend/api/tasks.py)

Endpoints (SSE follows existing chat streaming style):
- `POST /api/tasks` → create task; body: `TaskCreatePayload`
  - If `dry_run=true`: return planned JSON for user approval (status remains PLANNING|PENDING).
  - Else: persist task with status PENDING or RUNNING depending on dispatcher pickup.
- `GET /api/tasks` → list TaskSummary
- `GET /api/tasks/{task_id}` → TaskDetail
- `GET /api/tasks/{task_id}/stream` → SSE stream (subscribe to events)
- `POST /api/tasks/{task_id}/pause`
- `POST /api/tasks/{task_id}/resume`
- `POST /api/tasks/{task_id}/cancel`

Status rules:
- pause: RUNNING → PAUSED
- resume: PENDING|PAUSED → RUNNING (dispatcher/worker will pick up)
- cancel: any non-terminal → CANCELED

### 8) Lifespan Integration (backend/main.py)

- Import and call `start_task_dispatcher()` inside `lifespan()` startup.
- Ensure graceful shutdown by signaling the dispatcher stop event.

---

## Frontend Changes

Minimal viable Tasks UI integrated with existing patterns.

### API Client (frontend/src/services/api.js)
Add functions:
- `createTask(payload)` → POST `/api/tasks`
- `listTasks()` → GET `/api/tasks`
- `getTaskDetail(id)` → GET `/api/tasks/{id}`
- `streamTask(id, callbacks, signal)` → GET `/api/tasks/{id}/stream` (SSE)
- `pauseTask(id)`, `resumeTask(id)`, `cancelTask(id)` → POST actions

### UI Components
- `TasksPanel.jsx`: list + create form (goal input, optional dry-run plan preview).
- `TaskDetail.jsx`: shows steps with statuses, logs, artifacts, live via SSE.
- “Promote to Task” action in chat message context menu to prefill the goal.
- Header indicator for running tasks count (optional).

### UX Details
- When a task is created with `conversation_id`, surface updates back into that conversation as assistant messages (final summary and a link to TaskDetail).
- Persist a minimal client-side cache; refetch on focus.
- Handle SSE abort via `AbortController` similar to chat streaming.

---

## Guardrails & Safety

- Tool Whitelist: enforce planner output tools ∈ allowed set.
- Budgets: default `max_seconds` (e.g., 3600) and `max_tool_calls` (e.g., 50); configurable via env.
- Timeouts: per-step timeout; abort on overrun with clear error.
- Retries: backoff (2^n * base), cap retries by `max_retries`.
- Sanitization: template variable replacement is read-only; no shell execution.
- Observability: structured logs for each step and top-level task transitions.

---

## Prompts (Initial Versions)

### Planning Prompt (system)
- You are a planning agent. Produce an execution plan as strict JSON matching the provided schema. Use only the allowed tools; do not invent tools or parameters. Keep 3–10 steps. Each step must have: id, title, instruction, tool, params (if needed), success_criteria, max_retries. Keep success criteria concrete and testable.

### Planning Prompt (user inputs)
- Goal: "<USER_GOAL>"
- Resources available: brief description of existing MCP tools and their parameter shapes.
- Constraints: time budget (e.g., 60 minutes), tool-call budget.
- Output: only JSON per schema. No commentary.

### Verification Prompt (system)
- You are a verifier. Given a step’s success_criteria and its output, respond with a single JSON object: `{ "success": true|false, "reason": "one short sentence" }`.

### Retry Prompt (system)
- You are a remediation planner. Given the last error and the original step, produce an updated `params` (JSON only) that is more likely to succeed. If not possible, respond `{ "cannot_repair": true }`.

---

## Step-by-Step Implementation Plan

Follow these steps in order. You can ship in slices; each step ends in a verifiable checkpoint.

1) Models & CRUD
- Add Pydantic models to `backend/core/models.py` (TaskCreatePayload, TaskSummary, TaskDetail, Plan, PlanStep).
- Create `backend/db/tasks_crud.py` with create/read/update helpers and `create_indexes()`.
- Unit test CRUD functions with a test Mongo instance or mocks.

2) Planner
- Implement `backend/services/task_planner.py` with prompt builders and validation.
- Add `ALLOWED_TASK_TOOLS` constant.
- Write tests: mock Ollama to return a valid plan; validate whitelist rejection.

3) Runner (skeleton)
- Create `backend/services/task_runner.py` with dispatcher scaffolding and a no-op executor.
- Implement `resolve_tool()` and a small normalization layer for MCP responses.
- Add budget tracking and per-step timeout handling.

4) Progress Bus (SSE)
- Implement `backend/services/progress_bus.py` with subscribe/publish helpers.
- Wire runner to publish events; add simple unit test for the generator lifecycle.

5) API
- Add `backend/api/tasks.py` with routes: create/list/detail/stream/pause/resume/cancel.
- Return DTOs (Pydantic) from CRUD objects; ensure `response_model` correctness.
- Manual test with curl for task creation and event streaming.

6) Lifespan Integration
- In `backend/main.py`, start `start_task_dispatcher()` on app startup; ensure proper shutdown on exit.
- Add to `/api/status`: running tasks count (optional).

7) Minimal E2E
- Create a test task goal that uses web_search then python.create_plot on a provided CSV.
- Verify: plan is created; steps execute; SSE shows progress; task completes with summary.

8) Frontend API client
- Add task methods to `frontend/src/services/api.js`.
- Confirm fetch+SSE behavior mirrors chat streaming patterns; implement AbortController.

9) Frontend UI
- Create `TasksPanel.jsx` and `TaskDetail.jsx` with basic styles matching existing components.
- Add a top-level “Tasks” entry point (sidebar or header button).
- Add “Promote to Task” action in chat.

10) Hardening & Guardrails
- Add budgets/timeouts from env (e.g., `TASK_MAX_SECONDS_DEFAULT`, `TASK_MAX_TOOL_CALLS_DEFAULT`).
- Add verification prompt gate; log verifier results.
- Improve error messages; add unit tests for retries and budget exhaustion.

11) Docs & Operational Notes
- Update README with setup and usage.
- Add notes on Mongo indexes and known limitations (non-idempotent external tools, restart behavior).

---

## Mapping MCP Tools and Params (Initial)

- `web_search` (Web Search Server)
  - params: `{ "query": string }`
  - normalize: `{ text: formatted_summary }`
- `execute_sql_query_tool` (MySQL Server)
  - params: `{ "query": string }`
  - normalize: `{ rows: [...], columns: [...] }` or `{ error: string }`
- `get_youtube_transcript` (YouTube Server)
  - params: `{ "youtube_url": string }`
  - normalize: `{ text: transcript }` or `{ error: string }`
- `python.load_csv` (Python Server)
  - params: `{ "csv_b64": string }`
  - normalize: `{ text: status_message, df_id?: string }` (extract df_id via regex)
- `python.get_head`
  - params: `{ "df_id": string, "n"?: number }`
  - normalize: `{ text: head_table }`
- `python.get_descriptive_statistics`
  - params: `{ "df_id": string }`
  - normalize: `{ text: stats_table }`
- `python.create_plot`
  - params: `{ "df_id": string, "plot_type": string, "x_col": string, "y_col"?: string }`
  - normalize: `{ image_b64: string }`
- `python.query_dataframe`
  - params: `{ "df_id": string, "query_string": string }`
  - normalize: `{ text: status_message, new_df_id?: string }`

---

## Testing Strategy

- Unit tests
  - Planner: schema adherence, tool whitelist enforcement, invalid JSON repair.
  - Runner: step execution happy path with mocked MCP responses; timeouts; retries.
  - Progress bus: subscribe/publish flow and cancellation.
- Integration tests
  - API routes with a fake Mongo and mocked planner/runner.
  - SSE end-to-end with a short plan.
- Manual tests
  - Create a task from the UI; watch live progress; pause/resume; verify persistence across server restart.

---

## Configuration

- Env vars (backend):
  - `TASK_MAX_SECONDS_DEFAULT` (e.g., 3600)
  - `TASK_MAX_TOOL_CALLS_DEFAULT` (e.g., 50)
  - `TASK_STEP_TIMEOUT_DEFAULT` (e.g., 120)
  - `TASK_DISPATCH_INTERVAL_MS` (e.g., 2000)
- Logging: reuse existing logging setup; add a dedicated logger namespace `task_runner`.

---

## Rollout Plan

1. Land models + CRUD + planner (dry-run only) behind a feature flag (e.g., `ENABLE_TASKS=true`).
2. Add runner + SSE with basic tools; keep UI minimal.
3. Dogfood internally overnight on safe goals.
4. Harden guardrails and add budgets/timeouts.
5. Expand UI and docs; enable by default.

---

## Future Enhancements

- Multi-worker queue (Redis + RQ/Arq) for concurrency and resilience.
- Notification integrations (email/webhooks) on completion/failure.
- Rich artifact storage (GridFS) for large files.
- Plan revision mid-run with LLM when blocked.
- Tool set expansion (HTTP fetcher, vector search) with strict scopes.

---

## Checklist (Developer)

- [ ] Add models to `core/models.py` and implement `db/tasks_crud.py`
- [ ] Implement `services/task_planner.py` with schema prompt and validation
- [ ] Implement `services/task_runner.py` (dispatcher, execution, evaluation, budgets)
- [ ] Implement `services/progress_bus.py`
- [ ] Add `api/tasks.py` endpoints and wire router in `backend/main.py`
- [ ] Start dispatcher in FastAPI lifespan; expose status in `/api/status`
- [ ] Add API client functions in `frontend/src/services/api.js`
- [ ] Build `TasksPanel.jsx` and `TaskDetail.jsx`; add UI affordances
- [ ] E2E test a short plan; verify persistence and SSE
- [ ] Update README with setup and feature overview

---

By following this plan, you’ll introduce robust, resumable, long-running task execution that leverages the existing MCP tool ecosystem and streaming UX patterns already present in the app.

