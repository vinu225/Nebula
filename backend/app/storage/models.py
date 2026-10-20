"""
Sovereign AI Workbench — SQLAlchemy Database Models

Schema for:
- Sessions & Conversation Messages
- Tasks & Multi-Step Execution Plans
- Ingested Documents & Vector Chunks (pgvector)
- Generated Artifacts
- Sovereignty & Compliance Audit Trail
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    Vector = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base declarative class."""
    pass


class SessionModel(Base):
    """User conversation and task session."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), default="New Session")
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, default="default_user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active, completed, archived
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    messages: Mapped[List[MessageModel]] = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan")
    tasks: Mapped[List[TaskModel]] = relationship("TaskModel", back_populates="session", cascade="all, delete-orphan")
    artifacts: Mapped[List[ArtifactModel]] = relationship("ArtifactModel", back_populates="session", cascade="all, delete-orphan")
    documents: Mapped[List[DocumentModel]] = relationship("DocumentModel", back_populates="session", cascade="all, delete-orphan")


class MessageModel(Base):
    """Chat message inside a session."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(32))  # user, assistant, system, tool
    content: Mapped[str] = mapped_column(Text, default="")
    model_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tool_calls: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    tool_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[SessionModel] = relationship("SessionModel", back_populates="messages")


class TaskModel(Base):
    """Agentic task execution breakdown."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, planning, executing, completed, failed
    plan: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    skill_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[SessionModel] = relationship("SessionModel", back_populates="tasks")
    steps: Mapped[List[TaskStepModel]] = relationship("TaskStepModel", back_populates="task", cascade="all, delete-orphan")


class TaskStepModel(Base):
    """Individual sub-step inside an agent task."""

    __tablename__ = "task_steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    step_index: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    tool_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, in_progress, completed, failed
    input_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    task: Mapped[TaskModel] = relationship("TaskModel", back_populates="steps")


class DocumentModel(Base):
    """Ingested source document (e.g. PDF, P&ID drawing, inspection sheet)."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(32))
    storage_path: Mapped[str] = mapped_column(String(512))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    is_scanned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[Optional[SessionModel]] = relationship("SessionModel", back_populates="documents")
    chunks: Mapped[List[DocumentChunkModel]] = relationship("DocumentChunkModel", back_populates="document", cascade="all, delete-orphan")


class DocumentChunkModel(Base):
    """Text chunk of a document with embedding vector for local RAG."""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(64), ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # 768 dimensions for nomic-embed-text or all-minilm (fallback to JSON if pgvector not enabled)
    if HAS_PGVECTOR and Vector is not None:
        embedding = mapped_column(Vector(768), nullable=True)
    else:
        embedding = mapped_column(JSON, nullable=True)

    document: Mapped[DocumentModel] = relationship("DocumentModel", back_populates="chunks")


class ArtifactModel(Base):
    """Generated artifact (Word doc, PPT, Excel, script, PDF)."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(32))  # docx, pptx, xlsx, py, pdf, png
    storage_path: Mapped[str] = mapped_column(String(512))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[SessionModel] = relationship("SessionModel", back_populates="artifacts")


class AuditLogModel(Base):
    """Immutable audit trail ensuring sovereignty and compliance logging."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)  # model_call, tool_exec, network_intercept, error
    actor: Mapped[str] = mapped_column(String(64), default="agent")
    model_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32))  # success, failure, blocked
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
