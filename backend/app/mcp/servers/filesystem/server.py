"""
Sovereign AI Workbench — Sandboxed Filesystem MCP Server

Exposes workspace file read/write/list operations.
Strictly prevents path traversal outside the designated workspace directory.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _resolve_safe_path(user_path: str) -> Path:
    """Resolve and verify path is strictly within settings.workspace_dir."""
    base = settings.workspace_dir.resolve()
    resolved = (base / user_path).resolve()
    if not str(resolved).startswith(str(base)):
        raise PermissionError(f"Access denied: Path '{user_path}' escapes workspace sandbox.")
    return resolved


def fs_list_directory(rel_path: str = ".") -> List[Dict[str, Any]]:
    """List contents of a directory in the workspace."""
    target = _resolve_safe_path(rel_path)
    if not target.exists() or not target.is_dir():
        return []

    items = []
    for entry in target.iterdir():
        items.append({
            "name": entry.name,
            "is_dir": entry.is_dir(),
            "size_bytes": entry.stat().st_size if entry.is_file() else 0,
        })
    return items


def fs_read_file(rel_path: str) -> str:
    """Read contents of a text file in the workspace."""
    target = _resolve_safe_path(rel_path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"File not found: {rel_path}")
    return target.read_text(encoding="utf-8", errors="replace")


def fs_write_file(rel_path: str, content: str) -> Dict[str, Any]:
    """Write text content to a file in the workspace."""
    target = _resolve_safe_path(rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": str(target.relative_to(settings.workspace_dir.resolve())), "size_bytes": len(content)}
