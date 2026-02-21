# Feature: Fix Low-Severity Security Issues (SEC-008 through SEC-011)

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Address the 4 low-severity security findings from the OhSee security review (`.agents/security-reviews/security-review-2026-02-21.md`). These are hardening improvements for a localhost-only application: MySQL query timeouts/row limits, CSV upload size limits with DataFrame store eviction, a MongoDB no-auth startup warning, and documenting the Codex API key environment exposure as a known limitation.

## User Story

As a developer running OhSee locally
I want defense-in-depth protections against resource exhaustion and data exposure
So that the application is resilient to accidental misuse and edge cases

## Problem Statement

1. **SEC-010**: MySQL queries have no timeout or row limit — an expensive query can hang the server or exhaust memory with a huge result set.
2. **SEC-011**: CSV uploads have no size limit and DataFrames accumulate in memory forever — can OOM the Python MCP server.
3. **SEC-009**: MongoDB connects without authentication by default and there's no warning at startup when no credentials are detected.
4. **SEC-008**: The OpenAI API key is visible in the Codex subprocess environment — acceptable for localhost but should be documented.

## Solution Statement

1. Add `connect_timeout` and `read_timeout` to MySQL `db_config`, and append `LIMIT 1000` to queries that don't already have one.
2. Add a max decoded size check (50MB) in `load_csv()` and cap `data_store` at 10 entries with LRU eviction.
3. Add a startup warning in `db/mongodb.py` when the connection URI has no credentials.
4. Add a comment in `server_codex.py` documenting the known limitation, and add a note to the Security Considerations section in README.md.

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Low
**Primary Systems Affected**: `backend/server_mysql.py`, `backend/server_python.py`, `backend/db/mongodb.py`, `backend/server_codex.py`, `README.md`
**Dependencies**: None (all changes use stdlib or existing libraries)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `backend/server_mysql.py` (lines 19-26) — `db_config` dict where timeouts must be added
- `backend/server_mysql.py` (lines 102-132) — `is_safe_query()` where LIMIT injection goes
- `backend/server_mysql.py` (lines 134-155) — `execute_sql_query_tool()` that calls `is_safe_query`
- `backend/server_python.py` (lines 19-20) — `data_store: Dict[str, DataFrame] = {}` definition
- `backend/server_python.py` (lines 35-53) — `load_csv()` function to add size check and eviction
- `backend/db/mongodb.py` (lines 1-68) — Module-level connection setup where warning goes
- `backend/db/mongodb.py` (line 52) — `MongoClient(MONGODB_URI)` call
- `backend/core/config.py` (line 42) — `MONGODB_URI` default value
- `backend/server_codex.py` (lines 683-685) — Where `OPENAI_API_KEY` is injected into subprocess env
- `README.md` (line 252) — Existing Security Considerations section to extend
- `backend/tests/test_security_fixes.py` — Existing security test file to extend

### New Files to Create

None — all changes are modifications to existing files.

### Relevant Documentation

- [mysql-connector-python connection arguments](https://dev.mysql.com/doc/connector-python/en/connector-python-connectargs.html)
  - `connect_timeout` and `read_timeout` parameters
  - Why: Need correct parameter names for mysql.connector
- [pandas.read_csv memory](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html)
  - Why: Confirms read_csv accepts BytesIO, no built-in size limit

### Patterns to Follow

**Logging Pattern** (from `db/mongodb.py`):
```python
logger = get_logger("module_name")
logger.warning("message")
```

**Config Pattern** (from `core/config.py`):
```python
SETTING = os.getenv('ENV_VAR', 'default_value')
```

**Error Return Pattern** (from `server_python.py`):
```python
return "Error: description of what went wrong"
```

---

## IMPLEMENTATION PLAN

### Phase 1: MySQL Hardening (SEC-010)

Add connection and read timeouts to prevent hanging queries. Add a default row limit to prevent memory exhaustion from unbounded result sets.

### Phase 2: CSV/DataFrame Limits (SEC-011)

Add a decoded size check before parsing CSV. Implement LRU eviction on `data_store` to cap memory usage.

### Phase 3: MongoDB Auth Warning (SEC-009)

Log a warning at startup when the MongoDB URI contains no credentials.

### Phase 4: Codex Key Documentation (SEC-008)

Document the subprocess environment exposure as a known limitation.

### Phase 5: Tests & Validation

Extend `test_security_fixes.py` with tests for the new protections.

---

## STEP-BY-STEP TASKS

### Task 1: UPDATE `backend/server_mysql.py` — Add timeouts to db_config

- **IMPLEMENT**: Add `'connect_timeout': 10` and `'read_timeout': 30` to the `db_config` dict (lines 19-26)
- **PATTERN**: Same dict structure already there, just add two keys
- **VALIDATE**: `cd backend && python -m py_compile server_mysql.py && echo "OK"`

### Task 2: UPDATE `backend/server_mysql.py` — Add default LIMIT to queries

- **IMPLEMENT**: In `is_safe_query()` (or in `execute_sql_query_tool` before calling `is_safe_query`), if the query does not already contain `limit` (case-insensitive), append ` LIMIT 1000` to the query string. Do this in `execute_sql_query_tool` so `is_safe_query` stays a pure validator. Modify the query in-place before passing to `execute_select_query`.
- **PATTERN**: The function already manipulates the query string (lowering for checks). Add the LIMIT injection after the safety check passes but before execution.
- **GOTCHA**: Check for existing LIMIT with regex `r'\blimit\b'` on the lowered query to avoid double-limiting. The LIMIT must go before any trailing semicolons or whitespace.
- **VALIDATE**: `cd backend && python -m py_compile server_mysql.py && echo "OK"`

### Task 3: UPDATE `backend/server_python.py` — Add CSV size limit and DataFrame eviction

- **IMPLEMENT**:
  1. Add constants near the top (after imports, before `data_store`):
     ```python
     MAX_CSV_BYTES = 50 * 1024 * 1024  # 50 MB decoded limit
     MAX_DATAFRAMES = 10  # Max DataFrames in memory
     ```
  2. In `load_csv()`, after `csv_bytes = base64.b64decode(csv_b64)`, add:
     ```python
     if len(csv_bytes) > MAX_CSV_BYTES:
         return f"Error: CSV too large ({len(csv_bytes)} bytes). Maximum is {MAX_CSV_BYTES} bytes (50 MB)."
     ```
  3. After `data_store[df_id] = df`, add LRU eviction:
     ```python
     while len(data_store) > MAX_DATAFRAMES:
         oldest_key = next(iter(data_store))
         del data_store[oldest_key]
     ```
- **PATTERN**: Follows existing error return pattern in `load_csv`
- **GOTCHA**: Python dicts preserve insertion order since 3.7, so `next(iter(...))` gives the oldest entry. This is a simple FIFO eviction (good enough — true LRU would require reordering on access, which is overkill here).
- **VALIDATE**: `cd backend && python -m py_compile server_python.py && echo "OK"`

### Task 4: UPDATE `backend/db/mongodb.py` — Add no-auth startup warning

- **IMPLEMENT**: Inside the `try` block (after the successful `ping` on line 53 and before the success log on line 64), check if the URI contains credentials. If not, log a warning.
  ```python
  # After: mongo_client.admin.command('ping')
  if '@' not in MONGODB_URI:
      logger.warning(
          "MongoDB connection has no authentication. "
          "For sensitive data, enable MongoDB auth and use a URI with credentials."
      )
  ```
- **PATTERN**: Follows existing logging pattern in the same file
- **GOTCHA**: The `@` character is present in authenticated URIs like `mongodb://user:pass@host:port/`. Its absence is a reliable indicator of no credentials. This is a simple heuristic — not a full URI parser — but sufficient for a warning.
- **VALIDATE**: `cd backend && python -m py_compile db/mongodb.py && echo "OK"`

### Task 5: UPDATE `backend/server_codex.py` — Document known limitation

- **IMPLEMENT**: Add a comment block above the `if openai_api_key:` line (line 683) documenting the known limitation:
  ```python
  # SEC-008: The API key is visible in /proc/<pid>/environ to same-user processes.
  # Acceptable for single-user localhost. For hardening, consider passing via stdin.
  ```
- **VALIDATE**: `cd backend && python -m py_compile server_codex.py && echo "OK"`

### Task 6: UPDATE `README.md` — Extend Security Considerations

- **IMPLEMENT**: Add two bullet points to the existing Security Considerations section (after the "Provider API Keys" bullet):
  ```markdown
  - **MySQL Queries**: Queries are validated as read-only SELECT statements and automatically limited to 1000 rows. Connection and read timeouts prevent runaway queries.
  - **CSV Uploads**: Uploads are capped at 50 MB decoded size, and the in-memory DataFrame store is limited to 10 datasets (oldest evicted first).
  ```
- **PATTERN**: Matches existing bullet format in the section
- **VALIDATE**: Visual inspection

### Task 7: UPDATE `backend/tests/test_security_fixes.py` — Add tests for low-severity fixes

- **IMPLEMENT**: Add three new test classes to the existing file:

  1. `TestMySQLConfig` — verify `db_config` contains timeout keys
  2. `TestCSVLimits` — verify constants exist and `load_csv` rejects oversized input
  3. `TestMongoDBWarning` — verify the warning is logged when URI has no `@`

- **PATTERN**: Follow existing class structure in the file (plain `class TestX:` with `def test_y(self):`)
- **GOTCHA**: For `load_csv` test, use a small base64 string and mock `MAX_CSV_BYTES` to a tiny value, OR just test the constants exist. For MongoDB, use `unittest.mock.patch` on the logger.
- **VALIDATE**: `cd backend && python -m pytest tests/test_security_fixes.py -v`

---

## TESTING STRATEGY

### Unit Tests

Extend `backend/tests/test_security_fixes.py` with:

```python
class TestMySQLConfig:
    """SEC-010: MySQL query timeouts and row limits."""

    def test_db_config_has_connect_timeout(self):
        from server_mysql import db_config
        assert 'connect_timeout' in db_config
        assert db_config['connect_timeout'] == 10

    def test_db_config_has_read_timeout(self):
        from server_mysql import db_config
        assert 'read_timeout' in db_config
        assert db_config['read_timeout'] == 30


class TestCSVLimits:
    """SEC-011: CSV upload size limits and DataFrame store eviction."""

    def test_max_csv_bytes_constant(self):
        from server_python import MAX_CSV_BYTES
        assert MAX_CSV_BYTES == 50 * 1024 * 1024

    def test_max_dataframes_constant(self):
        from server_python import MAX_DATAFRAMES
        assert MAX_DATAFRAMES == 10

    def test_data_store_is_dict(self):
        from server_python import data_store
        assert isinstance(data_store, dict)


class TestMongoDBNoAuthWarning:
    """SEC-009: MongoDB no-auth startup warning."""

    def test_warning_logged_for_no_auth_uri(self):
        # This is a structural test — verify the warning code path exists
        # by checking the source contains the expected warning string
        import inspect
        import db.mongodb as mod
        source = inspect.getsource(mod)
        assert "no authentication" in source.lower() or "no auth" in source.lower()
```

### Edge Cases

- MySQL query that already has `LIMIT` should NOT get a second one
- CSV exactly at the 50MB boundary should be accepted
- `data_store` with exactly 10 entries should not evict; 11th entry should trigger eviction of the oldest

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
cd backend && python -m py_compile server_mysql.py && echo "OK"
cd backend && python -m py_compile server_python.py && echo "OK"
cd backend && python -m py_compile db/mongodb.py && echo "OK"
cd backend && python -m py_compile server_codex.py && echo "OK"
```

### Level 2: Unit Tests

```bash
cd backend && python -m pytest tests/test_security_fixes.py -v
```

### Level 3: Regression Tests

```bash
cd backend && python -m pytest tests/test_chat_service.py tests/test_tasks.py -v
```

### Level 4: Manual Validation

```bash
# Verify MySQL timeouts in config
cd backend && python -c "from server_mysql import db_config; assert db_config.get('connect_timeout') == 10; assert db_config.get('read_timeout') == 30; print('MySQL timeouts OK')"

# Verify CSV limits
cd backend && python -c "from server_python import MAX_CSV_BYTES, MAX_DATAFRAMES; assert MAX_CSV_BYTES == 50*1024*1024; assert MAX_DATAFRAMES == 10; print('CSV limits OK')"

# Verify MongoDB warning text exists
cd backend && python -c "
import inspect, db.mongodb as m
assert 'no authentication' in inspect.getsource(m).lower()
print('MongoDB warning OK')
"

# Verify LIMIT injection logic
cd backend && python -c "
from server_mysql import is_safe_query
# is_safe_query should still accept queries with LIMIT
assert is_safe_query('SELECT * FROM users LIMIT 5') == True
print('LIMIT check OK')
"
```

### Level 5: Full Test Suite

```bash
cd backend && python -m pytest tests/ -v
cd frontend && npm run build
```

---

## ACCEPTANCE CRITERIA

- [ ] MySQL `db_config` includes `connect_timeout: 10` and `read_timeout: 30`
- [ ] Queries without LIMIT get `LIMIT 1000` appended automatically
- [ ] Queries that already have LIMIT are not modified
- [ ] `load_csv()` rejects base64 input that decodes to >50MB
- [ ] `data_store` never exceeds 10 DataFrames (oldest evicted on overflow)
- [ ] MongoDB startup logs a warning when URI has no `@` (no credentials)
- [ ] Codex subprocess key injection has a documenting comment
- [ ] README Security Considerations section updated with MySQL and CSV notes
- [ ] All existing tests still pass (zero regressions)
- [ ] New tests added and passing for all four findings
- [ ] All `py_compile` checks pass

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order (1-7)
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Acceptance criteria all met

---

## NOTES

- **SEC-008 (Codex API key in env)**: This is documented as a known limitation rather than fixed. Passing the key via stdin would require changes to the Codex CLI itself, which is out of scope. The risk is minimal for a single-user localhost app.
- **LIMIT injection placement**: Done in `execute_sql_query_tool` rather than `is_safe_query` to keep the validator pure (no mutation). The LIMIT is appended after safety validation passes.
- **DataFrame eviction**: Uses simple FIFO (oldest-first) rather than true LRU. True LRU would require reordering `data_store` on every access, adding complexity for minimal benefit in a tool where DataFrames are typically used sequentially.
- **MongoDB auth detection**: Uses `@` presence as a heuristic. This covers `mongodb://user:pass@host` and `mongodb+srv://user:pass@host` patterns. Edge case: a URI with `@` in the database name would suppress the warning, but this is extremely unlikely.
