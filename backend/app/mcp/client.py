"""
Sovereign AI Workbench — Unified MCP & Tool Client

Aggregates native tools, filesystem operations, and sandbox execution
into a standardized registry for LangGraph agents.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.mcp.servers.filesystem.server import fs_list_directory, fs_read_file, fs_write_file
from app.mcp.servers.sandbox.server import mcp_execute_python, mcp_run_tests
from app.tools.calculator import evaluate_math
from app.tools.ocr import perform_ocr
from app.tools.pdf import parse_pdf
from app.tools.rag import search_knowledge_base

logger = get_logger(__name__)


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolRegistry:
    """Manages all available tools callable by the agent."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Any]] = {}
        self._definitions: Dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        # Calculator
        self.register(
            name="calculator",
            description="Evaluate mathematical and engineering calculations safely",
            func=evaluate_math,
            parameters={"expression": {"type": "string", "description": "Mathematical expression to evaluate"}},
        )

        # PDF Parser
        self.register(
            name="pdf_parser",
            description="Extract text and metadata from PDF files",
            func=parse_pdf,
            parameters={"file_path": {"type": "string", "description": "Path to PDF file"}},
        )

        # Local OCR
        self.register(
            name="ocr",
            description="Extract text from scanned drawings, forms, and images using local OCR",
            func=perform_ocr,
            parameters={"image_input": {"type": "string", "description": "Path to image or PDF page"}},
        )

        # RAG Knowledge Search
        self.register(
            name="rag_search",
            description="Search on-premise knowledge base for SOPs, equipment standards, and manuals",
            func=search_knowledge_base,
            parameters={"query": {"type": "string", "description": "Search query"}},
        )

        # Filesystem MCP
        self.register(
            name="fs_read",
            description="Read file contents from the workspace",
            func=fs_read_file,
            parameters={"rel_path": {"type": "string", "description": "Relative path in workspace"}},
        )
        self.register(
            name="fs_write",
            description="Write content to a file in the workspace",
            func=fs_write_file,
            parameters={
                "rel_path": {"type": "string", "description": "Relative path in workspace"},
                "content": {"type": "string", "description": "File text content"},
            },
        )
        self.register(
            name="fs_list",
            description="List directory contents in the workspace",
            func=fs_list_directory,
            parameters={"rel_path": {"type": "string", "description": "Relative directory path", "default": "."}},
        )

        # Sandbox MCP
        self.register(
            name="execute_python",
            description="Run Python code in the isolated air-gapped Docker sandbox",
            func=mcp_execute_python,
            parameters={"code": {"type": "string", "description": "Python source code"}},
        )
        self.register(
            name="run_tests",
            description="Run Python code and unit tests together in the sandbox",
            func=mcp_run_tests,
            parameters={
                "code": {"type": "string", "description": "Implementation code"},
                "test_code": {"type": "string", "description": "Unit test code"},
            },
        )

    def register(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._tools[name] = func
        self._definitions[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters or {},
        )

    def get_tool(self, name: str) -> Optional[Callable[..., Any]]:
        return self._tools.get(name)

    def list_definitions(self) -> List[ToolDefinition]:
        return list(self._definitions.values())

    async def invoke_tool(self, name: str, **kwargs: Any) -> Any:
        """Call a tool asynchronously."""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found in registry")

        import inspect
        if inspect.iscoroutinefunction(tool):
            return await tool(**kwargs)
        else:
            return tool(**kwargs)


_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
