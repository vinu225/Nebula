"""
Sovereign AI Workbench — Session Management API

Endpoints for creating, listing, inspecting, and deleting agent sessions.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.storage.database import get_db
from app.storage.models import ArtifactModel, MessageModel, SessionModel, TaskModel

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionCreateRequest(BaseModel):
    title: str = Field(default="New Sovereign Session")
    user_id: Optional[str] = Field(default="operator_1")


class SessionResponse(BaseModel):
    id: str
    title: str
    user_id: Optional[str]
    status: str
    created_at: str
    updated_at: str


class SessionDetailResponse(SessionResponse):
    messages: List[Dict[str, Any]] = []
    tasks: List[Dict[str, Any]] = []
    artifacts: List[Dict[str, Any]] = []


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Create a new agent workspace session."""
    session_id = str(uuid.uuid4())
    session_obj = SessionModel(
        id=session_id,
        title=payload.title,
        user_id=payload.user_id,
    )
    db.add(session_obj)
    await db.commit()
    await db.refresh(session_obj)

    return SessionResponse(
        id=session_obj.id,
        title=session_obj.title,
        user_id=session_obj.user_id,
        status=session_obj.status,
        created_at=session_obj.created_at.isoformat(),
        updated_at=session_obj.updated_at.isoformat(),
    )


@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> List[SessionResponse]:
    """List recent sessions."""
    stmt = select(SessionModel).order_by(desc(SessionModel.updated_at)).limit(limit)
    res = await db.execute(stmt)
    sessions = res.scalars().all()

    return [
        SessionResponse(
            id=s.id,
            title=s.title,
            user_id=s.user_id,
            status=s.status,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionDetailResponse:
    """Retrieve full details of a session including history and artifacts."""
    stmt = (
        select(SessionModel)
        .where(SessionModel.id == session_id)
        .options(
            selectinload(SessionModel.messages),
            selectinload(SessionModel.tasks),
            selectinload(SessionModel.artifacts),
        )
    )
    res = await db.execute(stmt)
    session_obj = res.scalar_one_or_none()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    messages_data = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "model_name": m.model_name,
            "created_at": m.created_at.isoformat(),
        }
        for m in session_obj.messages
    ]

    tasks_data = [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "plan": t.plan,
            "created_at": t.created_at.isoformat(),
        }
        for t in session_obj.tasks
    ]

    artifacts_data = [
        {
            "id": a.id,
            "name": a.name,
            "file_type": a.file_type,
            "size_bytes": a.size_bytes,
            "download_url": f"/api/artifacts/{a.id}/download",
            "created_at": a.created_at.isoformat(),
        }
        for a in session_obj.artifacts
    ]

    return SessionDetailResponse(
        id=session_obj.id,
        title=session_obj.title,
        user_id=session_obj.user_id,
        status=session_obj.status,
        created_at=session_obj.created_at.isoformat(),
        updated_at=session_obj.updated_at.isoformat(),
        messages=messages_data,
        tasks=tasks_data,
        artifacts=artifacts_data,
    )


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Delete an individual chat message by ID."""
    stmt = select(MessageModel).where(MessageModel.id == message_id)
    res = await db.execute(stmt)
    msg = res.scalar_one_or_none()
    if msg:
        await db.delete(msg)
        await db.commit()
    return {"status": "success", "id": message_id}


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a session and all its associated messages and artifacts."""
    stmt = select(SessionModel).where(SessionModel.id == session_id)
    res = await db.execute(stmt)
    session_obj = res.scalar_one_or_none()
    if session_obj:
        await db.delete(session_obj)
        await db.commit()


class SessionUpdateRequest(BaseModel):
    title: str


@router.patch("/{session_id}")
async def update_session(
    session_id: str,
    payload: SessionUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update a session's title."""
    stmt = select(SessionModel).where(SessionModel.id == session_id)
    res = await db.execute(stmt)
    session_obj = res.scalar_one_or_none()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    session_obj.title = payload.title
    await db.commit()
    return {"status": "success", "id": session_id, "title": session_obj.title}

