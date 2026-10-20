"""
Sovereign AI Workbench — Audit Logger

Maintains an immutable record of all agent decisions, model selections,
tool calls, file access, and security checks for refinery regulatory compliance.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.storage.database import get_db_context
from app.storage.models import AuditLogModel

logger = get_logger(__name__)

# In-memory buffer of recent events for quick dashboard access
_in_memory_audit_trail: List[Dict[str, Any]] = []
_MAX_BUFFER_SIZE = 500


async def log_audit_event(
    event_type: str,
    status: str = "success",
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    actor: str = "agent",
    model_name: Optional[str] = None,
    tool_name: Optional[str] = None,
    duration_ms: Optional[float] = None,
    ip_address: Optional[str] = "127.0.0.1",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Record an audit event to memory buffer and PostgreSQL."""
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    event_dict = {
        "id": event_id,
        "session_id": session_id,
        "task_id": task_id,
        "event_type": event_type,
        "status": status,
        "actor": actor,
        "model_name": model_name,
        "tool_name": tool_name,
        "duration_ms": duration_ms,
        "ip_address": ip_address,
        "details": details or {},
        "timestamp": now.isoformat(),
    }

    _in_memory_audit_trail.append(event_dict)
    if len(_in_memory_audit_trail) > _MAX_BUFFER_SIZE:
        _in_memory_audit_trail.pop(0)

    try:
        async with get_db_context() as db:
            db_entry = AuditLogModel(
                id=event_id,
                session_id=session_id,
                task_id=task_id,
                event_type=event_type,
                actor=actor,
                model_name=model_name,
                tool_name=tool_name,
                status=status,
                duration_ms=duration_ms,
                ip_address=ip_address,
                details=details or {},
                timestamp=now,
            )
            db.add(db_entry)
    except Exception as e:
        logger.warning("audit_db_write_failed_kept_in_memory", reason=str(e))

    logger.info("audit_logged", event_type=event_type, status=status, tool=tool_name, model=model_name)
    return event_dict


def get_in_memory_audit_trail(limit: int = 50) -> List[Dict[str, Any]]:
    """Return latest audit events in reverse chronological order."""
    return list(reversed(_in_memory_audit_trail))[:limit]
