"""
Unit tests for MCP Client, Sandbox Security, and Filesystem operations.
"""

from __future__ import annotations

import pytest

from app.mcp.client import get_tool_registry
from app.mcp.servers.filesystem.server import fs_list_directory, fs_read_file, fs_write_file
from app.sandbox.docker_executor import get_sandbox_executor
from app.sandbox.security import validate_python_code


def test_sandbox_security_blocks_socket_and_system() -> None:
    unsafe_code = """
import socket
s = socket.socket()
"""
    is_safe, violations = validate_python_code(unsafe_code)
    assert not is_safe
    assert any("socket" in v for v in violations)


def test_sandbox_security_allows_safe_math() -> None:
    safe_code = """
import math

def calculate(x):
    return math.sqrt(x) * 2

result = calculate(16)
print(result)
"""
    is_safe, violations = validate_python_code(safe_code)
    assert is_safe
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_sandbox_execution_safe_code() -> None:
    executor = get_sandbox_executor()
    code = "print(sum([1, 2, 3, 4, 5]))"
    res = await executor.execute_code(code)
    assert res["success"] is True
    assert "15" in res["stdout"]


def test_filesystem_mcp_sandboxed() -> None:
    write_res = fs_write_file("test_mcp_file.txt", "Sovereign Industrial Data")
    assert write_res["size_bytes"] > 0

    read_content = fs_read_file("test_mcp_file.txt")
    assert read_content == "Sovereign Industrial Data"

    files = fs_list_directory(".")
    assert any(f["name"] == "test_mcp_file.txt" for f in files)


def test_filesystem_mcp_blocks_traversal() -> None:
    with pytest.raises(PermissionError):
        fs_read_file("../../outside.txt")


@pytest.mark.asyncio
async def test_tool_registry_invocation() -> None:
    registry = get_tool_registry()
    calc_res = await registry.invoke_tool("calculator", expression="50 * 2")
    assert calc_res == "100"
