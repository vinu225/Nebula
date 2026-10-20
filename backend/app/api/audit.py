"""
Sovereign AI Workbench — Audit & Sovereignty API

Endpoints powering the real-time Security and Compliance Dashboard.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.logger import get_in_memory_audit_trail
from app.security.network import get_network_monitor
from app.storage.database import get_db
from app.storage.models import AuditLogModel

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/events", response_model=List[Dict[str, Any]])
async def get_audit_events(
    session_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get recent audit logs from database or memory buffer."""
    try:
        stmt = select(AuditLogModel).order_by(desc(AuditLogModel.timestamp)).limit(limit)
        if session_id:
            stmt = stmt.where(AuditLogModel.session_id == session_id)
        res = await db.execute(stmt)
        logs = res.scalars().all()
        if logs:
            return [
                {
                    "id": l.id,
                    "session_id": l.session_id,
                    "task_id": l.task_id,
                    "event_type": l.event_type,
                    "status": l.status,
                    "actor": l.actor,
                    "model_name": l.model_name,
                    "tool_name": l.tool_name,
                    "duration_ms": l.duration_ms,
                    "timestamp": l.timestamp.isoformat(),
                    "details": l.details,
                }
                for l in logs
            ]
    except Exception:
        pass

    # In-memory buffer fallback
    return get_in_memory_audit_trail(limit=limit)


@router.get("/sovereignty")
async def get_sovereignty_status() -> Dict[str, Any]:
    """Get security dashboard sovereignty & air-gap validation metrics."""
    monitor = get_network_monitor()
    return monitor.get_sovereignty_status()
