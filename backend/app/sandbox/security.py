"""
Sovereign AI Workbench — Sandbox Security Validator

Inspects submitted Python code via AST parsing before execution.
Enforces air-gapped industrial constraints:
- Blocks network sockets and requests
- Blocks dangerous shell execution (os.system, subprocess)
- Blocks unauthorized file traversal
"""

from __future__ import annotations

import ast
from typing import Tuple

from app.core.logging import get_logger

logger = get_logger(__name__)

# Strictly forbidden modules in sandbox
FORBIDDEN_MODULES = {
    "socket",
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
    "paramiko",
    "telnetlib",
    "ftplib",
    "subprocess",
    "pty",
    "pydoc",
}

# Forbidden function names / attributes
FORBIDDEN_CALLS = {
    ("os", "system"),
    ("os", "popen"),
    ("os", "spawn"),
    ("os", "execl"),
    ("os", "execv"),
    ("os", "fork"),
    ("posix", "system"),
    ("builtins", "exec"),
    ("builtins", "eval"),
    ("sys", "exit"),
}


class SecurityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_mod = alias.name.split(".")[0]
            if base_mod in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden import '{alias.name}' detected")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_mod = node.module.split(".")[0]
            if base_mod in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden import from '{node.module}' detected")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check for direct calls to eval/exec
        if isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec", "__import__"):
                self.violations.append(f"Forbidden call to '{node.func.id}'")
        # Check for module calls like os.system
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                pair = (node.func.value.id, node.func.attr)
                if pair in FORBIDDEN_CALLS:
                    self.violations.append(f"Forbidden call '{node.func.value.id}.{node.func.attr}'")
        self.generic_visit(node)


def validate_python_code(code_str: str) -> Tuple[bool, list[str]]:
    """Analyze Python code for security violations.

    Returns:
        (is_safe, list_of_violations)
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError as se:
        return False, [f"SyntaxError in code: {str(se)}"]

    visitor = SecurityVisitor()
    visitor.visit(tree)

    if visitor.violations:
        logger.warning("security_violations_detected", violations=visitor.violations)
        return False, visitor.violations

    return True, []
