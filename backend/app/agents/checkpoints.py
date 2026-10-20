"""
Sovereign AI Workbench — LangGraph Checkpointer

Provides state persistence for sessions using PostgreSQL async checkpointer
or graceful in-memory checkpointer fallback during local standalone development.
"""

from __future__ import annotations

import structlog
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

_memory_checkpointer = MemorySaver()
_postgres_checkpointer: BaseCheckpointSaver | None = None


async def get_checkpointer() -> BaseCheckpointSaver:
    """Obtain the configured checkpoint saver (Postgres or Memory)."""
    global _postgres_checkpointer

    if _postgres_checkpointer is not None:
        return _postgres_checkpointer

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        # Check if we can connect to postgres sync/async url
        # For simplicity and reliability in diverse local environments, attempt postgres connection
        async with AsyncPostgresSaver.from_conn_string(settings.database_url) as saver:
            await saver.setup()
            _postgres_checkpointer = saver
            logger.info("postgres_checkpoint_initialized")
            return _postgres_checkpointer
    except Exception as e:
        logger.warning(
            "postgres_checkpoint_unavailable_using_memory",
            reason=str(e),
        )
        return _memory_checkpointer
