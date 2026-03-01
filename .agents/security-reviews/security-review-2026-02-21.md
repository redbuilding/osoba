# Security Review — Osoba Codebase

**Date:** 2026-02-21
**Scope:** Full codebase (backend, frontend, MCP servers, scripts, dependencies)
**Context:** Locally-deployed application (localhost:8000 + localhost:5173)

---

## Executive Summary

Osoba has a reasonable security posture for a locally-deployed application. The codebase demonstrates intentional security thinking in several areas (SQL whitelist, Codex sandboxing, Fernet encryption, CORS restrictions). However, there are significant findings around arbitrary code execution via `pandas.DataFrame.query()`, XSS through unsanitized LLM output rendering, missing authentication on all API endpoints, and a service setup script that binds to `0.0.0.0`.

**Findings by severity:** 2 High, 5 Medium, 4 Low, 5 Info

**Top 3 priorities:**
1. Sandbox `pandas.DataFrame.query()` to prevent arbitrary Python execution (HIGH)
2. Sanitize HTML before `dangerouslySetInnerHTML` rendering in the frontend (HIGH)
3. Fix the macOS Launch Agent script binding to `0.0.0.0` instead of `127.0.0.1` (MEDIUM)

---

## Findings

### SEC-001
```
severity: high
domain: Input Validation
file: backend/server_python.py
line: 230, 254
title: pandas.DataFrame.query() allows arbitrary Python code execution
description: |
  Both `query_dataframe()` and `filter_dataframe()` pass user-controlled strings
  directly to `pandas.DataFrame.query()`. The `filter_dataframe` function has a
  basic keyword blocklist (`import`, `exec`, `eval`, `__`, `open`, `file`), but
  `query_dataframe()` has NO validation at all. Even the blocklist in
  `filter_dataframe` is trivially bypassable — pandas query uses numexpr/Python
  eval internally, and attackers can use string concatenation, attribute access,
  or @-variable references to bypass keyword checks.
  
  Example bypass: `@__builtins__.__import__('os').system('id')` or using
  backtick-quoted column names to inject expressions.
exploit scenario: |
  An LLM generates a malicious query string (via prompt injection in user input
  or a crafted CSV column name). The query executes arbitrary Python code in the
  server_python.py process, which has full filesystem access.
  
  In the task system, the planner generates query_string parameters autonomously,
  so a poisoned web search result could influence the planner to generate a
  malicious query.
recommendation: |
  1. Add the same (improved) validation to `query_dataframe` that `filter_dataframe` has.
  2. Replace the keyword blocklist with a proper allowlist approach. Consider using
     `pandas.eval()` with `engine='numexpr'` which is more restricted, or parse the
     expression with `ast` to verify it only contains comparisons and logical operators.
  3. At minimum, add these to the blocklist: `@`, `__builtins__`, `globals`, `locals`,
     `getattr`, `setattr`, `delattr`, `compile`, `type`, `lambda`, `os`, `sys`,
     `subprocess`, `shutil`.
effort: medium
```

### SEC-002
```
severity: high
domain: Frontend
file: frontend/src/components/ChatMessage.jsx
line: 109, 113
title: Unsanitized HTML rendering of LLM output enables XSS
description: |
  ChatMessage.jsx uses `dangerouslySetInnerHTML` to render both `indicator` HTML
  and `content` when `is_html` is true. The indicator HTML is constructed server-side
  from search results (titles, URLs) and tool outputs. The content includes LLM
  responses that may echo user input.
  
  MarkdownRenderer.jsx also uses `dangerouslySetInnerHTML` for all markdown content.
  While it escapes code blocks via `escapeHtml()`, the markdown processing functions
  (`processCompleteMarkdown`, `processMarkdownLine`) do NOT escape user text before
  wrapping it in HTML tags like `<h1>`, `<strong>`, `<li>`, `<td>`.
  
  For example, a heading like `# <img src=x onerror=alert(1)>` would be rendered as
  `<h1><img src=x onerror=alert(1)></h1>` — executing JavaScript.
exploit scenario: |
  1. A user sends a message containing `<script>` or `<img onerror=...>` tags.
     The LLM echoes it back. The frontend renders it as HTML.
  2. A web search result has a malicious title like `<img src=x onerror="fetch(...)">`.
     This gets injected into the indicator div without sanitization.
  3. In a multi-user scenario (if auth is ever added), this becomes a stored XSS
     vector since messages persist in MongoDB.
recommendation: |
  1. Use a sanitization library like DOMPurify before any `dangerouslySetInnerHTML`:
     ```jsx
     import DOMPurify from 'dompurify';
     dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(content) }}
     ```
  2. In MarkdownRenderer, escape all text content before wrapping in HTML tags.
     The `escapeHtml()` function already exists — apply it to heading text, list
     items, bold/italic content, and table cells.
  3. For indicators, sanitize server-side before sending (escape HTML entities in
     search result titles and URLs).
effort: low
```

### SEC-003
```
severity: medium
domain: Deployment
file: scripts/setup-macos-service.sh
line: 62-63
title: Launch Agent binds to 0.0.0.0, exposing backend to the network
description: |
  The generated plist file uses `--host 0.0.0.0` which binds the backend to all
  network interfaces. This exposes the unauthenticated API to the local network
  (and potentially the internet if port-forwarded or on a public network).
  
  Combined with SEC-004 (no API authentication), any device on the same network
  can access all endpoints: read conversations, create tasks, manage API keys,
  trigger heartbeats, etc.
exploit scenario: |
  User runs the setup script on a laptop connected to a coffee shop WiFi.
  Another device on the same network discovers port 8000 and accesses all
  conversations, stored API keys (via the settings endpoint which strips keys
  but the save endpoint accepts them), and can create tasks that execute
  arbitrary tool calls.
recommendation: |
  Change line 63 from `--host 0.0.0.0` to `--host 127.0.0.1`:
  ```xml
  <string>--host</string>
  <string>127.0.0.1</string>
  ```
  This matches the `main.py` default which correctly uses `127.0.0.1`.
effort: low
```

### SEC-004
```
severity: medium
domain: Auth
file: backend/main.py (all routes)
title: No authentication on any API endpoint
description: |
  The entire API surface (chat, tasks, conversations, provider settings, heartbeat,
  memory, profiles, codex) has zero authentication. All endpoints use a hardcoded
  `user_id = "default"`. Anyone who can reach the backend can read all data and
  perform all actions.
  
  For localhost-only deployment this is acceptable, but it becomes critical if
  combined with SEC-003 (0.0.0.0 binding) or if the user ever exposes the port.
exploit scenario: |
  If the backend is accidentally exposed (via SEC-003, ngrok, port forwarding,
  or running in a container with published ports), an attacker gets full access
  to all conversations, stored API keys, and can execute arbitrary tasks.
recommendation: |
  For now, document this as an explicit design decision in README.md:
  "⚠️ Osoba has no authentication. Never expose port 8000 to untrusted networks."
  
  For future hardening:
  1. Add a simple bearer token or basic auth middleware
  2. Generate a random token on first run, store in .env, require it in headers
  3. This would protect against accidental network exposure
effort: medium (for basic token auth), high (for full user auth)
```

### SEC-005
```
severity: medium
domain: Secrets
file: backend/db/settings_crud.py
line: 10-13
title: Auto-generated Fernet key on missing SETTINGS_ENCRYPTION_KEY loses keys on restart
description: |
  When `SETTINGS_ENCRYPTION_KEY` is not set, the code generates a random Fernet key
  at import time and logs a warning. This means:
  1. Every backend restart generates a new key
  2. All previously encrypted API keys become undecryptable
  3. The decrypt function silently returns "" for undecryptable keys
  
  While the fallback behavior (treating as missing) is safe, users who skip the
  .env setup step will repeatedly lose their provider API keys without understanding why.
exploit scenario: |
  Not a direct exploit, but a usability/reliability issue that could lead users to
  store API keys in less secure ways (e.g., hardcoding in source files) out of
  frustration.
recommendation: |
  1. On startup, if SETTINGS_ENCRYPTION_KEY is missing, log an ERROR (not warning)
     with clear instructions to generate and set the key.
  2. Consider refusing to start the settings encryption module without the key,
     or at minimum, persist the auto-generated key to a file so it survives restarts.
  3. Add a startup health check that validates the key can decrypt existing records.
effort: low
```

### SEC-006
```
severity: medium
domain: Auth
file: backend/auth_hubspot.py
line: 18, 80-81
title: HubSpot OAuth has no CSRF protection (missing state parameter)
description: |
  The OAuth flow in `hubspot_connect()` does not include a `state` parameter in the
  authorization URL. The callback endpoint `hubspot_oauth_callback()` does not verify
  any state parameter. This makes the flow vulnerable to CSRF attacks where an attacker
  could trick a user into authorizing the attacker's HubSpot account.
  
  Additionally, the session cookie is set with `samesite='lax'` but without `secure=True`,
  which is fine for localhost HTTP but would be insecure if ever served over HTTPS.
exploit scenario: |
  An attacker crafts a link to `/auth/hubspot/connect` and tricks the user into clicking
  it. The user authorizes their HubSpot account, and the token is stored in the attacker's
  session (if the attacker can control the session cookie). In practice, this is low risk
  for localhost but would be critical if the app were ever exposed.
recommendation: |
  1. Generate a random `state` parameter, store it in the session, and verify it in the
     callback:
     ```python
     state = str(uuid4())
     # Store state in session/cookie
     params['state'] = state
     ```
  2. In the callback, verify `request.query_params.get('state')` matches the stored value.
effort: low
```

### SEC-007
```
severity: medium
domain: MCP
file: backend/services/task_planner.py
line: 1-33 (ALLOWED_TASK_TOOLS)
title: Task system tool whitelist is enforced at plan time but not at execution time
description: |
  The `ALLOWED_TASK_TOOLS` list is checked during plan generation (tools not in the list
  are skipped). However, `_resolve_tool()` in task_runner.py does not re-validate against
  the whitelist — it resolves any tool that matches its routing patterns.
  
  If a plan document is manually modified in MongoDB (or if the planner's JSON parsing
  is manipulated), a tool outside the whitelist could be executed.
exploit scenario: |
  An attacker with MongoDB access (or via a NoSQL injection, though none were found)
  modifies a task's plan to include a tool not in ALLOWED_TASK_TOOLS. The runner would
  execute it if it matches a known routing pattern. In practice, this is limited because
  _resolve_tool raises ValueError for truly unknown tools.
recommendation: |
  Add a whitelist check in `_execute_step()` before calling `_resolve_tool()`:
  ```python
  if tool not in ALLOWED_TASK_TOOLS and not tool.startswith("llm."):
      raise RuntimeError(f"Tool '{tool}' not in allowed whitelist")
  ```
effort: low
```

### SEC-008
```
severity: low
domain: Secrets
file: backend/server_codex.py
line: 498 (env["OPENAI_API_KEY"] = openai_api_key)
title: OpenAI API key visible in process environment
description: |
  The OpenAI API key is passed to the Codex subprocess via environment variables.
  On Linux/macOS, any process running as the same user can read another process's
  environment via `/proc/<pid>/environ` (Linux) or `ps eww` (macOS).
  
  The code does redact the key from stdout/stderr logs, which is good.
exploit scenario: |
  Another process running as the same user on the machine could read the Codex
  subprocess's environment to extract the OpenAI API key. This requires local
  access as the same user, making it low severity for a single-user local app.
recommendation: |
  This is an acceptable trade-off for a local app. For hardening:
  1. Consider passing the key via stdin to the subprocess instead of env
  2. Or use a temporary file with restricted permissions (0600) that's deleted after read
  Document this as a known limitation.
effort: medium
```

### SEC-009
```
severity: low
domain: Data
file: backend/db/mongodb.py
title: MongoDB connection uses no authentication by default
description: |
  The default MongoDB URI is `mongodb://localhost:27017/` with no username or password.
  MongoDB's default installation also has no authentication enabled. This means any
  process on the machine can read/write all Osoba data.
  
  The data includes: conversation history, user profiles, stored (encrypted) API keys,
  task plans and outputs, heartbeat insights, and semantic memory metadata.
exploit scenario: |
  Another application or malware on the same machine connects to MongoDB and reads
  all conversation data. The encrypted API keys would still require the Fernet key
  to decrypt, but all other data is plaintext.
recommendation: |
  1. Document in README that users should enable MongoDB authentication for sensitive data
  2. Add a startup warning if connecting to MongoDB without authentication
  3. For the default local setup, this is acceptable — just make it explicit
effort: low
```

### SEC-010
```
severity: low
domain: Input Validation
file: backend/server_mysql.py
line: 87-107
title: SQL safety check is regex-based and potentially bypassable
description: |
  The `is_safe_query()` function uses regex to detect unsafe keywords. While it's
  a solid implementation (word boundary matching, comment blocking, semicolon blocking),
  regex-based SQL validation has known limitations:
  - Unicode homoglyphs could bypass keyword matching
  - Nested subqueries with CTEs might introduce edge cases
  - The function doesn't limit query complexity (e.g., expensive JOINs or subqueries
    could cause DoS on the database)
  
  However, the function correctly blocks comments, multiple statements, and all
  major DML/DDL keywords. For a read-only local tool, this is reasonable.
exploit scenario: |
  An LLM generates a query with an exotic bypass. In practice, the LLM is the
  intermediary (not direct user input), and the query must also be a valid SELECT
  statement, which significantly limits attack surface.
recommendation: |
  1. Consider adding a query timeout at the MySQL connection level:
     ```python
     db_config['connect_timeout'] = 10
     db_config['read_timeout'] = 30
     ```
  2. Add a result row limit (e.g., `LIMIT 1000`) to prevent memory exhaustion
  3. The current implementation is adequate for the threat model
effort: low
```

### SEC-011
```
severity: low
domain: Data
file: backend/server_python.py
title: No size limit on CSV uploads or in-memory DataFrame storage
description: |
  The `load_csv()` function accepts a base64-encoded CSV with no size limit.
  DataFrames are stored in an in-memory dict (`data_store`) with no eviction policy.
  A large CSV (or many CSVs) could exhaust server memory.
exploit scenario: |
  A user (or the task system) loads a very large CSV file, causing the Python MCP
  server subprocess to consume excessive memory and potentially crash.
recommendation: |
  1. Add a size check on the base64 input (e.g., max 50MB decoded)
  2. Limit the number of DataFrames in `data_store` (e.g., max 10, LRU eviction)
  3. Add a max row count check after loading
effort: low
```

### SEC-012
```
severity: info
domain: Frontend
file: frontend/src/App.jsx
line: 246, 813
title: localStorage used only for HubSpot auth flow state — no secrets stored
description: |
  The frontend uses localStorage only to track a pending HubSpot auth redirect
  (`pendingHubspotAuth`). No API keys, tokens, or sensitive data are stored
  client-side. The axios client uses `withCredentials: true` for cookie-based
  session management.
exploit scenario: None — this is a positive finding.
recommendation: No action needed. This is good practice.
effort: n/a
```

### SEC-013
```
severity: info
domain: Secrets
file: backend/.env.example
title: .env.example contains placeholder values, not real secrets
description: |
  The .env.example file correctly uses placeholder values like
  `your_serper_api_key_here`. The .gitignore should exclude `.env` (actual secrets).
exploit scenario: None — verify .gitignore includes `.env`.
recommendation: |
  Verify `.env` is in `.gitignore`. Also consider adding `backend/.env` explicitly
  since the .env file lives in the backend directory.
effort: low
```

### SEC-014
```
severity: info
domain: Dependencies
file: backend/requirements.txt, frontend/package.json
title: Dependency versions are loosely pinned
description: |
  Backend: Most packages have no version pins (e.g., `fastapi`, `uvicorn`, `pymongo`).
  Some have minimum versions (`trafilatura>=1.6.0`, `chromadb>=0.4.0`).
  Frontend: Uses caret ranges (`^1.9.0`, `^18.2.0`).
  
  This means `pip install` and `npm install` will pull latest compatible versions,
  which could introduce breaking changes or vulnerabilities.
recommendation: |
  1. Generate a `requirements.txt` with pinned versions: `pip freeze > requirements.lock`
  2. Use `npm shrinkwrap` or commit `package-lock.json` for reproducible frontend builds
  3. Periodically run `pip audit` and `npm audit` to check for known vulnerabilities
effort: low
```

### SEC-015
```
severity: info
domain: Deployment
file: backend/main.py
line: 103-108
title: Development server defaults are appropriate for local use
description: |
  The `__main__` block correctly binds to `127.0.0.1` (not `0.0.0.0`), uses
  `--reload` for development, and restricts reload watching to the backend directory.
  The CORS policy correctly limits origins to `localhost:5173` and `127.0.0.1:5173`.
exploit scenario: None — this is a positive finding.
recommendation: No action needed for local deployment.
effort: n/a
```

### SEC-016
```
severity: info
domain: Secrets
file: backend/api/providers.py
line: 140-150
title: Settings endpoint correctly strips API keys from responses
description: |
  The `GET /api/settings` endpoint removes API keys from the response and replaces
  them with a `has_api_key` boolean. The `GET /api/providers/{id}/validate` endpoint
  returns only configuration status, never the key itself.
exploit scenario: None — this is a positive finding.
recommendation: No action needed. This is good practice.
effort: n/a
```

---

## Positive Security Practices

The codebase demonstrates several intentional security measures:

1. **SQL whitelist approach** — `is_safe_query()` blocks DML/DDL, comments, and multi-statements. Table name validation uses regex allowlist for `DESCRIBE` queries.

2. **Codex workspace isolation** — Dedicated per-run workspace, isolated HOME directory, symlink refusal, realpath containment checks, output policy enforcement, defense-in-depth rules blocking network/shell commands.

3. **Fernet encryption for API keys** — Provider API keys are encrypted at rest in MongoDB. The decrypt function gracefully handles key rotation (returns empty string, not ciphertext).

4. **CORS restrictions** — Limited to `localhost:5173` and `127.0.0.1:5173`. Not using wildcard `*`.

5. **Default localhost binding** — `main.py` binds to `127.0.0.1`, not `0.0.0.0`.

6. **API key redaction in Codex** — stdout/stderr from Codex runs are redacted for tokens and API keys before storage and return.

7. **Settings API strips secrets** — The GET settings endpoint never returns raw API keys.

8. **HubSpot token management** — Tokens stored in-memory (not persisted), with automatic refresh and cleanup on failure.

9. **Codex output policy** — Post-run enforcement of allowed extensions, file count limits, total byte limits, binary detection, and dotfile blocking.

10. **Log rotation** — Backend uses `RotatingFileHandler` with 5MB per file and 3 backups, preventing unbounded log growth.

---

## Recommendations Summary

### Immediate (High findings)
1. **SEC-001**: Add proper input validation to `query_dataframe()` and strengthen `filter_dataframe()` blocklist. Consider AST-based validation or switching to `engine='numexpr'`.
2. **SEC-002**: Add DOMPurify to the frontend and sanitize all `dangerouslySetInnerHTML` usage. Apply `escapeHtml()` in MarkdownRenderer to non-code-block content.

### Short-term (Medium findings, quick wins)
3. **SEC-003**: Change `0.0.0.0` to `127.0.0.1` in `setup-macos-service.sh` (one-line fix).
4. **SEC-006**: Add `state` parameter to HubSpot OAuth flow (small change, two files).
5. **SEC-007**: Add whitelist re-check in `_execute_step()` before tool resolution.
6. **SEC-005**: Improve SETTINGS_ENCRYPTION_KEY missing behavior — log ERROR, consider persisting auto-generated key.
7. **SEC-004**: Add a security warning to README about never exposing port 8000.

### Long-term (Architectural improvements)
8. Add optional bearer token authentication for the API (protects against accidental exposure).
9. Pin dependency versions and set up automated vulnerability scanning (`pip audit`, `npm audit`).
10. Add MongoDB connection authentication documentation and startup warnings.
11. Implement CSV upload size limits and DataFrame store eviction in the Python MCP server.
12. Consider a proper HTML sanitization library server-side for indicator HTML construction.
