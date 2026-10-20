"""
Sovereign AI Workbench — FastAPI Application Entry Point

This is the main application module. It sets up:
- CORS middleware
- Lifespan handler (startup/shutdown)
- Router registration
- Application state (model registry, providers)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.models.registry import create_default_registry
from app.models.ollama import OllamaProvider
from app.storage.database import init_db
from app.agents.graph import compiled_agent_graph
from app.api import health, chat, sessions, files, artifacts, audit, skills, models, system
from app.services.model_manager import model_manager
from app.services.telemetry_service import telemetry_manager
from app.services.tts_service import tts_service

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler.

    Startup:
        - Initialize logging
        - Initialize database tables
        - Create model registry with Qwen models
        - Register Ollama provider
        - Verify Ollama connectivity

    Shutdown:
        - Clean up provider connections
    """
    settings = get_settings()

    # --- Startup ---
    setup_logging(log_level=settings.log_level, log_format=settings.log_format)
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        environment=settings.app_env,
        sovereign_mode=settings.sovereign_mode,
    )

    # Initialize database
    await init_db()

    # Create model registry
    registry = create_default_registry()

    # Create and register Ollama provider
    ollama_provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout,
    )
    registry.register_provider("ollama", ollama_provider)

    # Check Ollama health
    try:
        healthy = await ollama_provider.health_check()
        if healthy:
            logger.info("ollama_connected", base_url=settings.ollama_base_url)
            available = await ollama_provider.list_available_models()
            logger.info("ollama_models_available", models=available)
        else:
            logger.warning(
                "ollama_not_healthy",
                base_url=settings.ollama_base_url,
                message="Ollama is not responding. Models will not be available until Ollama starts.",
            )
    except Exception as e:
        logger.warning(
            "ollama_connection_failed",
            base_url=settings.ollama_base_url,
            error=str(e),
            message="Could not connect to Ollama. Start Ollama to enable model inference.",
        )

    # Store in app state
    app.state.model_registry = registry
    app.state.settings = settings
    app.state.agent_graph = compiled_agent_graph

    # Start 30-min model inactivity watchdog
    model_manager.start_watchdog(app.state)

    # Start Real-time Hardware Telemetry service
    telemetry_manager.start()

    # Pre-warm Piper TTS model in background
    import asyncio
    asyncio.create_task(asyncio.to_thread(tts_service.warmup))

    logger.info("application_started", sovereign_mode=settings.sovereign_mode)

    yield

    # --- Shutdown ---
    logger.info("application_shutting_down")
    telemetry_manager.stop()
    model_manager.stop_watchdog()
    await ollama_provider.close()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Sovereign On-Premise Agentic AI Workbench. "
            "All processing happens locally — no data leaves the system."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    # --- CORS (for frontend dev server) ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",   # Next.js dev server
            "http://127.0.0.1:3000",
            "http://localhost:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Register routers ---
    app.include_router(health.router)
    app.include_router(models.router)
    app.include_router(chat.router)
    app.include_router(sessions.router)
    app.include_router(files.router)
    app.include_router(artifacts.router)
    app.include_router(audit.router)
    app.include_router(skills.router)
    app.include_router(system.router)

    # Root endpoint
    @app.get("/")
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "sovereign_mode": settings.sovereign_mode,
            "status": "operational",
        }

    return app


# Application instance — used by `uvicorn app.main:app` or `uv run fastapi dev app/main.py`
app = create_app()
