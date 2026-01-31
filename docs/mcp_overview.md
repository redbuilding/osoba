# MCP Integration Overview for OhSee

This document summarizes MCP server possibilities for extending OhSee with external automations, local/system access, browser control, and local/remote LLMs, including integration patterns and safety considerations.

## External Automations (Zapier/Make)
- Capabilities: outbound actions (messaging, docs/CRMs, tickets), human-in-loop prompts, async orchestration.
- Two-way messaging: App sends via scenario/webhook; inbound replies hit an authenticated callback endpoint and resume tasks.
- Integration: Tools to trigger scenarios, await callbacks or poll storage, correlate via `correlation_id`.
- Safety: Scenario allowlists, typed schemas, minimal payloads, HMAC/timestamp/nonce on callbacks, idempotency, approval gates for high-risk actions.

## System Control MCP
- Read-first tools: `files.read/list/stat`, `code.search/symbols/diff`, `git.status/log/diff`, `processes/ports`, `logs.tail`, `system.info`.
- Controlled write tools: `files.write` with diffs, `git.commit` with approval, test/build runners, service restarts, package installs (gated).
- Knowledge packs: Repo index, test map, env snapshot, system state; large resources via stable URIs and summarized variants.
- Guardrails: Strong allowlists, JSON schemas (no raw shell), path normalization, sandboxing/containerization, least privilege, audit trails.

## Browser Automation MCP
- Approaches: Playwright (recommended), Selenium/WebDriver, Chrome CDP attach, OS UI scripting (limited).
- Tools: `start/open/click/type/wait/get_text/screenshot/pdf/cookies/close`; optional `evaluate` (disabled by default).
- Task fit: One session per task, artifact capture, summarize DOM before LLM.
- Risks & mitigations: Cookie/PII exposure, unintended actions, ToS/CAPTCHA. Use dedicated profiles, domain allowlists, approvals, sandboxing, rate limits, redaction, auditing.

## Gemini MCP (CLI/API)
- Options: Wrap local CLI (process bridge) or use Gemini API (preferred for stability/JSON).
- Tools: `generate`, `chat.new_session`/`chat.send`, `embed`, `count_tokens`, `models.list`, `files.upload` (API-backed).
- Considerations: Token/cost budgets, tool-use allowlists, streaming vs final outputs; avoid logging secrets; handle rate limits/retries.

## Security Themes
- Data minimization: Send only needed fields; assume external services log payloads.
- Auth & integrity: HMAC-signed callbacks, timestamp windows, nonces, idempotency keys, strict binding to expected task/session IDs.
- Policy & approvals: Per-tool scopes, allowlists, daily budgets, human approvals for messaging, writes, purchases, logins.
- Prompt-injection defenses: Quote external content, don’t let content set behavior, gate privileged tools.
- Observability: Redacted audit logs, metrics (latency, error rate), circuit breakers, dead-letter queues.

## macOS Operations
- Keep alive: Run as LaunchAgent with `KeepAlive`; prevent sleep with `caffeinate`; monitor via logs/`pmset -g assertions`.
- Inbound networking: Prefer callback mode on a stable host; otherwise use polling or secure tunnels (auth + signatures).
- Least privilege: Non-admin user, limited working dirs, no Full Disk Access; containerize risky MCPs where possible.

## Practical Starting Set
- MCPs to start: System (read-first), Playwright browser, Make (trigger + callback), Gemini API.
- Process: Define allowlists and JSON schemas; implement callback endpoint with HMAC and idempotency; add approval gates; log/audit; enforce budgets.

