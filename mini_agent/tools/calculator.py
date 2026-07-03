"""Safe arithmetic calculator tool."""

from __future__ import annotations

import ast
import operator

from mini_agent.tool_registry import Tool


_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.FloorDiv,
    ast.Mod,
)

_OPERATOR_MAP = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


def _eval(node: ast.AST) -> float:
    if not isinstance(node, _ALLOWED_NODES):
        raise ValueError(f"Unsupported expression element: {type(node).__name__}")
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Only numeric constants are allowed")
    if isinstance(node, ast.BinOp):
        op = _OPERATOR_MAP.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported binary operator: {type(node.op).__name__}")
        return op(_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.UAdd):
            return +_eval(node.operand)
        if isinstance(node.op, ast.USub):
            return -_eval(node.operand)
        raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
    raise ValueError(f"Could not evaluate node: {type(node).__name__}")


def calculator(expression: str) -> str:
    """Safely evaluate a numeric arithmetic expression."""
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        value = _eval(tree)
        # Return int-looking results as int for nicer output.
        if value == int(value):
            return str(int(value))
        return str(value)
    except Exception as exc:  # noqa: BLE001
        return f"Error: invalid expression ({exc})"


def get_tool() -> Tool:
    return Tool(
        name="calculator",
        description="Evaluate a safe arithmetic expression such as '1 + 2 * 3'.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A numeric arithmetic expression, e.g. '1+2*3'",
                },
            },
            "required": ["expression"],
        },
        func=calculator,
    )
