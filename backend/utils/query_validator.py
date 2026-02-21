"""AST-based expression validator for pandas query strings.

Parses expressions and allows only safe node types (comparisons, boolean ops,
names, constants). Rejects function calls, imports, attribute access to dunders,
and other code execution vectors.
"""

import ast
from typing import Tuple, Optional

# Node types allowed in pandas query expressions
_SAFE_NODE_TYPES = (
    ast.Expression,
    ast.BoolOp,       # and, or
    ast.BinOp,        # +, -, *, /
    ast.UnaryOp,      # not, ~, -
    ast.Compare,      # ==, !=, <, >, <=, >=, in, not in
    ast.Name,         # column names, True, False, None
    ast.Constant,     # string/number literals
    ast.Load,         # load context
    ast.And, ast.Or,  # boolean operators
    ast.Not,          # unary not
    ast.Invert, ast.UAdd, ast.USub,  # ~, +x, -x
    ast.BitAnd, ast.BitOr, ast.BitXor,  # &, |, ^ (pandas boolean ops)
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.FloorDiv,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.Tuple, ast.List,  # for `col.isin([1,2,3])` style comparisons
)

# Patterns that indicate code execution attempts
_FORBIDDEN_PREFIXES = ("__",)


def validate_query_expression(expr: str) -> Tuple[bool, Optional[str]]:
    """Validate a pandas query expression is safe to execute.

    Returns (True, None) if safe, or (False, error_message) if dangerous.
    """
    if not expr or not expr.strip():
        return False, "Empty expression"

    # Block @ references (pandas variable injection that can access Python scope)
    if "@" in expr:
        return False, "Forbidden character '@' in expression"

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        return False, f"Invalid expression syntax: {e}"

    for node in ast.walk(tree):
        # Reject any node type not in our allowlist
        if not isinstance(node, _SAFE_NODE_TYPES):
            return False, f"Forbidden expression element: {type(node).__name__}"

        # Block dunder names (e.g. __import__, __builtins__, __class__)
        if isinstance(node, ast.Name) and any(
            node.id.startswith(p) for p in _FORBIDDEN_PREFIXES
        ):
            return False, f"Forbidden identifier: {node.id}"

    return True, None
