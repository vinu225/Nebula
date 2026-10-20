"""
Sovereign AI Workbench — Safe Calculator Tool

Evaluates engineering calculations and arithmetic safely via Python AST parser.
Prevents arbitrary code execution.
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "pi": math.pi,
    "e": math.e,
}


def _eval_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _eval_node(node.operand)
        return _OPERATORS[op_type](operand)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple named function calls allowed")
        func_name = node.func.id
        if func_name not in _SAFE_FUNCTIONS:
            raise ValueError(f"Function '{func_name}' is not permitted")
        args = [_eval_node(arg) for arg in node.args]
        return _SAFE_FUNCTIONS[func_name](*args)
    elif isinstance(node, ast.Name):
        if node.id in _SAFE_FUNCTIONS:
            return _SAFE_FUNCTIONS[node.id]
        raise ValueError(f"Identifier '{node.id}' not allowed")
    else:
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def evaluate_math(expression: str) -> str:
    """Safely calculate the result of an arithmetic or engineering formula.

    Args:
        expression: e.g. "150 * 0.85 / (2 * 14000 - 1.2 * 150)"

    Returns:
        String result or error message.
    """
    try:
        expr = expression.strip()
        parsed = ast.parse(expr, mode="eval")
        result = _eval_node(parsed.body)
        logger.info("math_calculated", expression=expr, result=result)
        return str(result)
    except Exception as e:
        logger.error("math_calc_failed", expression=expression, error=str(e))
        return f"Error evaluating expression '{expression}': {str(e)}"
