"""Tests for security fixes (SEC-001 through SEC-007)."""

import pytest
from utils.query_validator import validate_query_expression
from services.task_planner import ALLOWED_TASK_TOOLS


class TestQueryValidator:
    """SEC-001: AST-based query expression validation."""

    # --- Safe expressions that MUST be allowed ---

    def test_simple_comparison(self):
        ok, err = validate_query_expression("age > 30")
        assert ok is True and err is None

    def test_compound_and(self):
        ok, _ = validate_query_expression("age > 30 and city == 'NYC'")
        assert ok is True

    def test_bitwise_and_or(self):
        ok, _ = validate_query_expression("(age > 30) & (city == 'NYC')")
        assert ok is True
        ok, _ = validate_query_expression("(a > 1) | (b < 2)")
        assert ok is True

    def test_in_operator(self):
        ok, _ = validate_query_expression('status in ["active", "pending"]')
        assert ok is True

    def test_not_operator(self):
        ok, _ = validate_query_expression("not is_deleted")
        assert ok is True

    def test_arithmetic_in_comparison(self):
        ok, _ = validate_query_expression("col1 + col2 > 100")
        assert ok is True

    def test_unary_negate(self):
        ok, _ = validate_query_expression("~is_deleted")
        assert ok is True

    def test_string_equality(self):
        ok, _ = validate_query_expression("name == 'Alice'")
        assert ok is True

    def test_numeric_range(self):
        ok, _ = validate_query_expression("age >= 18 and age <= 65")
        assert ok is True

    # --- Dangerous expressions that MUST be blocked ---

    def test_blocks_function_call(self):
        ok, err = validate_query_expression("eval('1+1')")
        assert ok is False
        assert "Call" in err

    def test_blocks_import(self):
        ok, err = validate_query_expression("__import__('os')")
        assert ok is False

    def test_blocks_at_reference(self):
        ok, err = validate_query_expression("@__builtins__")
        assert ok is False
        assert "@" in err

    def test_blocks_lambda(self):
        ok, err = validate_query_expression("lambda x: x")
        assert ok is False
        assert "Lambda" in err

    def test_blocks_attribute_access(self):
        ok, err = validate_query_expression("os.system('id')")
        assert ok is False

    def test_blocks_dunder_name(self):
        ok, err = validate_query_expression("__class__")
        assert ok is False
        assert "Forbidden identifier" in err

    def test_blocks_exec(self):
        ok, err = validate_query_expression("exec('print(1)')")
        assert ok is False

    def test_blocks_getattr(self):
        ok, err = validate_query_expression("getattr(df, '__class__')")
        assert ok is False

    # --- Edge cases ---

    def test_empty_string(self):
        ok, err = validate_query_expression("")
        assert ok is False

    def test_whitespace_only(self):
        ok, err = validate_query_expression("   ")
        assert ok is False

    def test_invalid_syntax(self):
        ok, err = validate_query_expression("age >>>> 30")
        assert ok is False
        assert "syntax" in err.lower()


class TestTaskWhitelist:
    """SEC-007: Task tool whitelist enforcement."""

    def test_web_search_in_whitelist(self):
        assert "web_search" in ALLOWED_TASK_TOOLS

    def test_smart_search_in_whitelist(self):
        assert "smart_search_extract" in ALLOWED_TASK_TOOLS

    def test_python_tools_in_whitelist(self):
        assert "python.load_csv" in ALLOWED_TASK_TOOLS
        assert "python.filter_dataframe" in ALLOWED_TASK_TOOLS

    def test_random_tool_not_in_whitelist(self):
        assert "malicious_tool" not in ALLOWED_TASK_TOOLS
        assert "shell_exec" not in ALLOWED_TASK_TOOLS


class TestOAuthState:
    """SEC-006: OAuth CSRF state parameter validation."""

    def test_oauth_states_dict_exists(self):
        from auth_hubspot import oauth_states
        assert isinstance(oauth_states, dict)

    def test_connect_endpoint_accepts_request_response(self):
        """Verify hubspot_connect signature includes request and response params."""
        import inspect
        from auth_hubspot import hubspot_connect
        sig = inspect.signature(hubspot_connect)
        assert "request" in sig.parameters
        assert "response" in sig.parameters

    def test_callback_endpoint_accepts_state(self):
        """Verify hubspot_oauth_callback signature includes state param."""
        import inspect
        from auth_hubspot import hubspot_oauth_callback
        sig = inspect.signature(hubspot_oauth_callback)
        assert "state" in sig.parameters
