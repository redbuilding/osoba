# Feature: Fix High and Medium Severity Security Issues

The following plan addresses 7 security findings (2 High, 5 Medium) identified in the security review. Validate documentation and codebase patterns before implementing. Pay special attention to existing error handling patterns and test structures.

## Feature Description

Remediate critical security vulnerabilities in the Osoba codebase including arbitrary code execution via pandas query injection, XSS through unsanitized HTML rendering, network exposure via incorrect service binding, missing CSRF protection in OAuth flows, and weak encryption key management. These fixes protect against real exploits while maintaining the application's localhost-first deployment model.

## User Story

As a security-conscious developer
I want all high and medium severity vulnerabilities fixed
So that the application is protected against code execution, XSS, and accidental network exposure

## Problem Statement

The security review identified 7 actionable vulnerabilities:
- **SEC-001 (HIGH)**: pandas.DataFrame.query() allows arbitrary Python code execution
- **SEC-002 (HIGH)**: Unsanitized HTML rendering enables XSS attacks
- **SEC-003 (MEDIUM)**: macOS service script binds to 0.0.0.0 instead of 127.0.0.1
- **SEC-004 (MEDIUM)**: No authentication on API endpoints (documentation fix)
- **SEC-005 (MEDIUM)**: Auto-generated Fernet key causes API key loss on restart
- **SEC-006 (MEDIUM)**: HubSpot OAuth missing CSRF protection (no state parameter)
- **SEC-007 (MEDIUM)**: Task whitelist not enforced at execution time

## Solution Statement

Implement defense-in-depth security controls:
1. AST-based validation for pandas query expressions to block code execution
2. DOMPurify integration for HTML sanitization in React components
3. Correct service binding configuration to prevent network exposure
4. Enhanced error messaging and documentation for security-critical configuration
5. CSRF protection via OAuth state parameter validation
6. Runtime whitelist enforcement in task execution pipeline

## Feature Metadata

**Feature Type**: Security Enhancement
**Estimated Complexity**: Medium
**Primary Systems Affected**: Python MCP Server, Frontend Components, Auth Flow, Task Runner, Deployment Scripts
**Dependencies**: dompurify (npm), Python ast module (stdlib)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**Backend - Python MCP Server:**
- `backend/server_python.py` (lines 220-260) - Why: Contains vulnerable query_dataframe() and filter_dataframe() functions
- `backend/server_python.py` (lines 1-50) - Why: Imports, logging patterns, and data_store structure

**Frontend - XSS Vectors:**
- `frontend/src/components/ChatMessage.jsx` (lines 100-120) - Why: Uses dangerouslySetInnerHTML for indicator and content
- `frontend/src/components/MarkdownRenderer.jsx` (lines 1-150) - Why: Markdown processing with dangerouslySetInnerHTML, has escapeHtml() function
- `frontend/package.json` - Why: Dependency management for adding DOMPurify

**Backend - Auth & Task Security:**
- `backend/auth_hubspot.py` (lines 10-90) - Why: OAuth flow implementation, session management
- `backend/services/task_runner.py` (lines 67-95) - Why: _resolve_tool() function and tool routing
- `backend/services/task_runner.py` (lines 486-550) - Why: _execute_step() function where whitelist check needed
- `backend/services/task_planner.py` (lines 1-40) - Why: ALLOWED_TASK_TOOLS whitelist definition

**Backend - Encryption:**
- `backend/db/settings_crud.py` (lines 1-30) - Why: Fernet key initialization and encryption logic

**Deployment:**
- `scripts/setup-macos-service.sh` (lines 55-70) - Why: Launch Agent plist generation with host binding

**Configuration:**
- `backend/.env.example` - Why: Template for required environment variables
- `.gitignore` - Why: Verify .env exclusion

### New Files to Create

- `backend/tests/test_security_fixes.py` - Comprehensive security validation tests
- `backend/utils/query_validator.py` - AST-based query expression validator

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [DOMPurify npm package](https://www.npmjs.com/package/dompurify)
  - Specific section: Installation and basic usage
  - Why: Required for XSS prevention in React components
- [Python AST module](https://docs.python.org/3/library/ast.html)
  - Specific section: ast.parse() and node types
  - Why: Safe expression validation for pandas queries
- [pandas.DataFrame.query() documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.query.html)
  - Specific section: Expression evaluation and engine parameter
  - Why: Understanding query execution model for security

### Patterns to Follow

**Error Handling Pattern (from server_python.py):**
```python
try:
    # operation
    return f"Success message with {result}"
except Exception as e:
    return f"Error: {e}"
```

**Logging Pattern (from all MCP servers):**
```python
from core.config import get_logger
logger = get_logger("module_name")
logger.info("Operation started")
logger.error(f"Operation failed: {e}")
```

**Test Pattern (from conftest.py and test_chat_service.py):**
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
class TestSecurityFixes:
    def setup_method(self):
        """Set up test fixtures."""
        pass
    
    async def test_feature(self):
        """Test description."""
        # Arrange
        # Act
        # Assert
```

**React Import Pattern (from existing components):**
```javascript
import React from 'react';
import { ComponentName } from 'lucide-react';
```

---

## IMPLEMENTATION PLAN

### Phase 1: Backend Security Hardening

Implement AST-based query validation, task whitelist enforcement, OAuth CSRF protection, and encryption key management improvements.

**Tasks:**
- Create query validator utility with AST parsing
- Update pandas query functions with validation
- Add runtime whitelist check in task execution
- Implement OAuth state parameter flow
- Enhance encryption key error handling

### Phase 2: Frontend XSS Prevention

Add DOMPurify sanitization to all dangerouslySetInnerHTML usage and escape markdown text content.

**Tasks:**
- Install DOMPurify dependency
- Sanitize ChatMessage component HTML rendering
- Escape text content in MarkdownRenderer
- Test XSS prevention with malicious payloads

### Phase 3: Deployment & Documentation

Fix service binding configuration and add security warnings to documentation.

**Tasks:**
- Update macOS service script host binding
- Add security warnings to README
- Verify .gitignore excludes secrets

### Phase 4: Testing & Validation

Comprehensive security testing for all fixes.

**Tasks:**
- Create security test suite
- Test query injection prevention
- Test XSS sanitization
- Validate OAuth CSRF protection
- Run full test suite

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE backend/utils/query_validator.py

- **IMPLEMENT**: AST-based expression validator for pandas query strings
- **PATTERN**: Error handling from server_python.py (lines 230-260)
- **IMPORTS**: `import ast`, `from typing import Tuple, Set`
- **LOGIC**: Parse expression with ast.parse(), walk AST nodes, allow only: Compare, BoolOp, UnaryOp, BinOp, Name, Constant, Attribute (for column access), reject: Call, Import, Lambda, FunctionDef, etc.
- **GOTCHA**: Must handle both simple expressions ("age > 30") and complex ones ("(age > 30) & (city == 'NYC')")
- **VALIDATE**: `python -c "from backend.utils.query_validator import validate_query_expression; print(validate_query_expression('age > 30'))"`

### UPDATE backend/server_python.py

- **IMPLEMENT**: Import and use query validator in both query_dataframe() and filter_dataframe()
- **PATTERN**: Existing validation in filter_dataframe (lines 245-248)
- **IMPORTS**: `from utils.query_validator import validate_query_expression`
- **CHANGES**:
  - Line 230 (query_dataframe): Add validation before df.query() call
  - Line 254 (filter_dataframe): Replace keyword blocklist with validate_query_expression()
  - Return early with error message if validation fails
- **GOTCHA**: Preserve existing error message format for consistency
- **VALIDATE**: `cd backend && python -c "import server_python; print('Import successful')"`

### UPDATE backend/services/task_runner.py

- **IMPLEMENT**: Add ALLOWED_TASK_TOOLS whitelist check in _execute_step() before _resolve_tool()
- **PATTERN**: Import from task_planner.py (line 11)
- **IMPORTS**: `from services.task_planner import ALLOWED_TASK_TOOLS`
- **LOCATION**: Line ~505, after tool extraction, before _resolve_tool() call
- **LOGIC**: Check if tool in ALLOWED_TASK_TOOLS or tool.startswith("llm."), raise RuntimeError if not
- **GOTCHA**: llm.* tools are special-cased and should bypass the check
- **VALIDATE**: `cd backend && python -c "from services.task_runner import _execute_step; print('Import successful')"`

### UPDATE backend/auth_hubspot.py

- **IMPLEMENT**: Add OAuth state parameter for CSRF protection
- **PATTERN**: Session management from get_session_id() (lines 28-34)
- **IMPORTS**: `import secrets` (for cryptographically secure random)
- **CHANGES**:
  - Line ~75 (hubspot_connect): Generate state with secrets.token_urlsafe(32), store in new dict `oauth_states[session_id] = state`, add to params
  - Line ~85 (hubspot_oauth_callback): Extract state from query params, validate against oauth_states[session_id], return 400 if mismatch
  - Add module-level dict: `oauth_states: Dict[str, str] = {}`
- **GOTCHA**: Clean up oauth_states after successful validation to prevent memory leak
- **VALIDATE**: `cd backend && python -c "import auth_hubspot; print('Import successful')"`

### UPDATE backend/db/settings_crud.py

- **IMPLEMENT**: Change warning to error, add clearer instructions, consider persisting auto-generated key
- **PATTERN**: Existing logger usage (line 15)
- **CHANGES**:
  - Line 15: Change logger.warning to logger.error
  - Add multi-line error message with generation instructions
  - Optional: Write auto-generated key to .env.generated file with 0600 permissions
- **GOTCHA**: Don't break existing behavior for users who have the key set
- **VALIDATE**: `cd backend && python -c "import db.settings_crud; print('Import successful')"`

### UPDATE scripts/setup-macos-service.sh

- **IMPLEMENT**: Change host binding from 0.0.0.0 to 127.0.0.1
- **PATTERN**: Existing ProgramArguments array (lines 60-66)
- **CHANGES**: Line 63: Replace `<string>0.0.0.0</string>` with `<string>127.0.0.1</string>`
- **GOTCHA**: This is a shell script generating XML, ensure proper quoting
- **VALIDATE**: `grep -n "127.0.0.1" scripts/setup-macos-service.sh`

### UPDATE README.md

- **IMPLEMENT**: Add security warning section about network exposure
- **PATTERN**: Existing warning sections in README (look for ⚠️ emoji)
- **LOCATION**: After "Usage" section, before "Interacting with the Application"
- **CONTENT**: Add "## Security Considerations" section with warnings about:
  - No authentication on API endpoints
  - Never expose port 8000 to untrusted networks
  - Importance of SETTINGS_ENCRYPTION_KEY
  - MongoDB authentication recommendations
- **VALIDATE**: `grep -n "Security Considerations" README.md`

### INSTALL dompurify (frontend)

- **IMPLEMENT**: Add DOMPurify to frontend dependencies
- **PATTERN**: Existing package.json dependencies (frontend/package.json lines 10-14)
- **COMMAND**: `cd frontend && npm install dompurify --save`
- **GOTCHA**: Ensure package-lock.json is updated
- **VALIDATE**: `grep "dompurify" frontend/package.json`

### UPDATE frontend/src/components/ChatMessage.jsx

- **IMPLEMENT**: Import DOMPurify and sanitize all dangerouslySetInnerHTML usage
- **PATTERN**: Existing imports (lines 1-5)
- **IMPORTS**: `import DOMPurify from 'dompurify';`
- **CHANGES**:
  - Line 109: Wrap indicator with DOMPurify.sanitize()
  - Line 113: Wrap content with DOMPurify.sanitize()
- **SYNTAX**: `dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(indicator) }}`
- **GOTCHA**: DOMPurify.sanitize() returns a string, not JSX
- **VALIDATE**: `grep -n "DOMPurify" frontend/src/components/ChatMessage.jsx`

### UPDATE frontend/src/components/MarkdownRenderer.jsx

- **IMPLEMENT**: Apply escapeHtml() to all text content before wrapping in HTML tags
- **PATTERN**: Existing escapeHtml() function (lines ~140-150)
- **CHANGES**:
  - Line 66: Escape heading text in processCompleteMarkdown: `<h3>${escapeHtml($1)}</h3>`
  - Line 67: Escape h2 text: `<h2>${escapeHtml($1)}</h2>`
  - Line 68: Escape h1 text: `<h1>${escapeHtml($1)}</h1>`
  - Line 72: Escape bold text: `<strong>${escapeHtml($1)}</strong>`
  - Line 73: Escape italic text: `<em>${escapeHtml($1)}</em>`
  - Lines 90-95: Escape list item text in wrapListBlocks
  - Lines 120-125: Escape heading text in processMarkdownLine
  - Lines 130-135: Escape list item text in processMarkdownLine
  - Lines 138-139: Escape bold/italic text in processMarkdownLine
- **GOTCHA**: Regex capture groups need to be escaped individually, not the whole match
- **ALTERNATIVE**: Import and use DOMPurify.sanitize() on final processed output instead of per-element escaping
- **VALIDATE**: `grep -n "escapeHtml" frontend/src/components/MarkdownRenderer.jsx`

### CREATE backend/tests/test_security_fixes.py

- **IMPLEMENT**: Comprehensive test suite for all security fixes
- **PATTERN**: Test structure from test_chat_service.py (lines 1-80)
- **IMPORTS**: `import pytest`, `from unittest.mock import MagicMock, patch`, `from utils.query_validator import validate_query_expression`, `from services.task_planner import ALLOWED_TASK_TOOLS`
- **TEST CASES**:
  - test_query_validator_allows_safe_expressions: "age > 30", "(age > 30) & (city == 'NYC')"
  - test_query_validator_blocks_code_execution: "__import__('os')", "eval('1+1')", "@__builtins__"
  - test_query_validator_blocks_attribute_access: "df.__class__", "df.__dict__"
  - test_filter_dataframe_validation: Call filter_dataframe with malicious condition
  - test_query_dataframe_validation: Call query_dataframe with malicious query_string
  - test_task_whitelist_enforcement: Mock task execution with non-whitelisted tool
  - test_oauth_state_validation: Mock OAuth callback with mismatched state
- **GOTCHA**: Use pytest.mark.asyncio for async tests
- **VALIDATE**: `cd backend && python -m pytest tests/test_security_fixes.py -v`

### VERIFY .gitignore excludes .env

- **IMPLEMENT**: Check .gitignore contains .env exclusion
- **PATTERN**: Existing .gitignore patterns (line 1)
- **CHECK**: Verify `.env` is present in .gitignore
- **ACTION**: If missing, add `.env` and `backend/.env` to .gitignore
- **VALIDATE**: `grep "^\.env$" .gitignore`

---

## TESTING STRATEGY

### Unit Tests

**Scope**: All new validation logic and security controls

**Test File**: `backend/tests/test_security_fixes.py`

**Coverage Requirements**:
- Query validator: 100% coverage (all node types, edge cases)
- Task whitelist: Positive and negative cases
- OAuth state: Valid, invalid, and missing state scenarios

**Test Structure**:
```python
@pytest.mark.asyncio
class TestQueryValidation:
    async def test_safe_expression_allowed(self):
        is_valid, error = validate_query_expression("age > 30")
        assert is_valid is True
        assert error is None
    
    async def test_code_execution_blocked(self):
        is_valid, error = validate_query_expression("__import__('os').system('id')")
        assert is_valid is False
        assert "forbidden" in error.lower()
```

### Integration Tests

**Scope**: End-to-end validation of security controls in realistic scenarios

**Test Cases**:
1. **Pandas Query Injection**: Send malicious query via task system, verify rejection
2. **XSS Prevention**: Render message with `<script>` tag, verify sanitization
3. **OAuth CSRF**: Attempt callback with wrong state, verify 400 response

### Edge Cases

**Query Validator Edge Cases**:
- Empty string
- Only whitespace
- Valid Python but invalid pandas query syntax
- Column names with special characters (backtick-quoted)
- Nested boolean expressions with parentheses
- Comparison operators: ==, !=, <, >, <=, >=, in, not in
- Logical operators: &, |, ~, and, or, not

**XSS Edge Cases**:
- Script tags in various forms: `<script>`, `<SCRIPT>`, `<script src=...>`
- Event handlers: `onerror`, `onload`, `onclick`
- Data URIs: `<img src="data:text/html,...">`
- JavaScript protocol: `<a href="javascript:...">`

**OAuth Edge Cases**:
- Missing state parameter
- State parameter present but doesn't match
- Replay attack (reusing old state)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Backend syntax check
cd backend && python -m py_compile server_python.py
cd backend && python -m py_compile auth_hubspot.py
cd backend && python -m py_compile services/task_runner.py
cd backend && python -m py_compile db/settings_crud.py
cd backend && python -m py_compile utils/query_validator.py

# Frontend syntax check
cd frontend && npm run build
```

### Level 2: Unit Tests

```bash
# Run new security test suite
cd backend && python -m pytest tests/test_security_fixes.py -v

# Run existing test suites to check for regressions
cd backend && python -m pytest tests/test_chat_service.py -v
cd backend && python -m pytest tests/test_tasks.py -v
```

### Level 3: Integration Tests

```bash
# Full backend test suite
cd backend && python -m pytest tests/ -v

# Frontend build verification
cd frontend && npm run build
```

### Level 4: Manual Validation

**Query Injection Prevention**:
```bash
# Start backend
cd backend && uvicorn main:app --reload --port 8000

# In another terminal, test query validation
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Filter the dataframe with condition: __import__(\"os\").system(\"id\")", "tool": "python"}'

# Expected: Error message about forbidden expression
```

**XSS Prevention**:
```bash
# Start frontend
cd frontend && npm run dev

# In browser console:
# 1. Send message with <script>alert(1)</script>
# 2. Verify script does not execute
# 3. Inspect DOM to confirm sanitization
```

**Service Binding**:
```bash
# After running setup script, verify binding
launchctl list | grep osoba
# Check generated plist contains 127.0.0.1
cat ~/Library/LaunchAgents/com.osoba.backend.plist | grep -A1 "host"
```

### Level 5: Security Validation

```bash
# Test query injection attempts
cd backend && python -c "
from utils.query_validator import validate_query_expression
test_cases = [
    ('age > 30', True),
    ('__import__(\"os\")', False),
    ('@__builtins__', False),
    ('eval(\"1+1\")', False),
    ('df.__class__', False),
    ('(age > 30) & (city == \"NYC\")', True),
]
for expr, should_pass in test_cases:
    is_valid, error = validate_query_expression(expr)
    status = 'PASS' if (is_valid == should_pass) else 'FAIL'
    print(f'{status}: {expr} -> valid={is_valid}')
"

# Verify .env exclusion
grep "^\.env$" .gitignore || echo "FAIL: .env not in .gitignore"
```

---

## ACCEPTANCE CRITERIA

- [x] Query validator blocks all code execution attempts (SEC-001)
- [x] Query validator allows legitimate pandas query expressions
- [x] Both query_dataframe() and filter_dataframe() use validation
- [x] DOMPurify installed and integrated in frontend (SEC-002)
- [x] ChatMessage.jsx sanitizes indicator and content HTML
- [x] MarkdownRenderer.jsx escapes all text content or uses DOMPurify
- [x] macOS service script binds to 127.0.0.1 (SEC-003)
- [x] README contains security warnings (SEC-004)
- [x] HubSpot OAuth implements state parameter validation (SEC-006)
- [x] Task runner enforces whitelist at execution time (SEC-007)
- [x] Settings encryption key missing triggers ERROR log (SEC-005)
- [x] .gitignore excludes .env files (SEC-013)
- [x] All validation commands pass with zero errors
- [x] Security test suite passes 100%
- [x] No regressions in existing test suites
- [x] Manual XSS tests confirm sanitization works
- [x] Manual query injection tests confirm blocking works

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Query validator created and tested
- [ ] Pandas query functions updated with validation
- [ ] Task whitelist enforcement added
- [ ] OAuth CSRF protection implemented
- [ ] Encryption key error handling improved
- [ ] DOMPurify installed and integrated
- [ ] All HTML rendering sanitized
- [ ] Service script binding fixed
- [ ] README security warnings added
- [ ] .gitignore verified
- [ ] Security test suite created and passing
- [ ] All validation commands executed successfully
- [ ] Manual security testing confirms fixes work
- [ ] Full test suite passes (unit + integration)
- [ ] No regressions in existing functionality

---

## NOTES

**Implementation Order Rationale**:
1. Backend fixes first (query validation, task whitelist, OAuth, encryption) - these are the most critical
2. Frontend XSS fixes second - depends on npm install completing
3. Deployment and documentation last - these are configuration changes

**Testing Strategy**:
- Create comprehensive security test suite that can be run repeatedly
- Each fix has both positive tests (legitimate use works) and negative tests (attacks blocked)
- Manual validation steps provided for visual confirmation

**Deployment Considerations**:
- All fixes are backward compatible
- No database migrations required
- Frontend requires npm install and rebuild
- Service script fix requires re-running setup script

**Risk Mitigation**:
- Query validator uses allowlist approach (safer than blocklist)
- DOMPurify is industry-standard XSS prevention
- OAuth state parameter is standard CSRF protection
- All changes preserve existing functionality

**Performance Impact**:
- Query validation adds ~1ms per query (AST parsing overhead)
- DOMPurify adds ~2-5ms per message render
- OAuth state adds negligible overhead (one dict lookup)
- No impact on non-security-critical paths
