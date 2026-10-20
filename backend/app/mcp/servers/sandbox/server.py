"""
Sovereign AI Workbench — Sandbox MCP Server

Exposes isolated code execution and test runner tools to the agent.
"""

from __future__ import annotations

from typing import Any, Dict

from app.core.logging import get_logger
from app.sandbox.docker_executor import get_sandbox_executor

logger = get_logger(__name__)


async def mcp_execute_python(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute Python code in isolated sandbox and return result."""
    executor = get_sandbox_executor()
    return await executor.execute_code(code=code, timeout=timeout)


async def mcp_run_tests(code: str, test_code: str, timeout: int = 30) -> Dict[str, Any]:
    """Run code and accompanying unit tests together."""
    combined_code = f"{code}\n\n# --- UNIT TESTS ---\n{test_code}\n\nif __name__ == '__main__':\n    import unittest\n    unittest.main(exit=False)\n"
    executor = get_sandbox_executor()
    return await executor.execute_code(code=combined_code, timeout=timeout)
