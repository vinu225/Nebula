"""
Sovereign AI Workbench — Database Engine and Session Management

Configures async SQLAlchemy engine with automatic reconnection, connection pooling,
and graceful fallback to SQLite for local zero-dependency testing if PostgreSQL is unavailable.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.storage.models import Base

logger = structlog.get_logger(__name__)

settings = get_settings()

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_using_sqlite_fallback: bool = False


def get_engine() -> AsyncEngine:
    """Obtain or initialize the global async engine."""
    global _engine, _session_factory, _using_sqlite_fallback

    if _engine is not None:
        return _engine

    db_url = settings.database_url

    # Check if postgres port is reachable
    import socket
    postgres_available = False
    try:
        sock = socket.create_connection(("localhost", 5432), timeout=0.2)
        sock.close()
        postgres_available = True
    except Exception:
        postgres_available = False

    if postgres_available:
        try:
            # Create async engine for Postgres
            _engine = create_async_engine(
                db_url,
                echo=settings.app_debug,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
            )
            _session_factory = async_sessionmaker(
                bind=_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
            logger.info("database_engine_created", url=db_url.split("@")[-1])
        except Exception as e:
            logger.warning("postgres_init_failed", error=str(e))
            postgres_available = False

    if not postgres_available:
        logger.info("postgres_unavailable_using_sqlite_fallback")
        return _init_sqlite_engine()

    return _engine


def _init_sqlite_engine() -> AsyncEngine:
    """Initialize or switch to the SQLite async engine fallback."""
    global _engine, _session_factory, _using_sqlite_fallback
    fallback_db_path = settings.workspace_dir / "sovereign_dev.db"
    fallback_url = f"sqlite+aiosqlite:///{fallback_db_path}"
    _engine = create_async_engine(
        fallback_url,
        echo=settings.app_debug,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    _using_sqlite_fallback = True
    logger.info("sqlite_fallback_engine_created", path=str(fallback_db_path))
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Obtain the configured async session factory."""
    global _session_factory
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


async def init_db() -> None:
    """Initialize database schemas and pgvector extension if available."""
    global _engine, _session_factory, _using_sqlite_fallback
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            # Enable pgvector if postgresql
            if "postgresql" in str(engine.url):
                try:
                    from sqlalchemy import text
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    logger.info("pgvector_extension_ensured")
                except Exception as ex:
                    logger.warning("pgvector_extension_init_skipped", reason=str(ex))

            await conn.run_sync(Base.metadata.create_all)
            logger.info("database_tables_initialized")
    except Exception as err:
        logger.warning("database_init_error_switching_to_sqlite", error=str(err))
        try:
            await engine.dispose()
        except Exception:
            pass
        engine = _init_sqlite_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database_tables_initialized_sqlite_fallback")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining async database sessions."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for standalone/service database operations."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
