"""
Sovereign AI Workbench — Health Check Endpoints

Provides health checks for the backend, Ollama, and all services.
Used by the frontend to display model/service status.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    details: dict | None = None


class ServiceStatusResponse(BaseModel):
    """Full service status response."""
    backend: str
    ollama: str
    models: dict[str, dict]
    sovereign_mode: bool


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic backend health check."""
    return HealthResponse(
        status="healthy",
        service="sovereign-ai-workbench",
        details={"version": "0.1.0"},
    )


@router.get("/models")
async def model_status(request: Request) -> dict:
    """Check availability of all registered models.

    Returns status for each model (ready / not_loaded / error).
    """
    registry = request.app.state.model_registry
    statuses = await registry.check_model_status()
    return {
        "models": statuses,
        "total": len(statuses),
        "ready": sum(1 for s in statuses.values() if s.get("ready")),
    }


@router.get("/services", response_model=ServiceStatusResponse)
async def service_status(request: Request) -> ServiceStatusResponse:
    """Check status of all services: backend, Ollama, models.

    Used by the frontend to populate the system status dashboard.
    """
    registry = request.app.state.model_registry
    ollama_provider = registry.get_provider("ollama")

    # Check Ollama health
    ollama_status = "offline"
    if ollama_provider:
        try:
            healthy = await ollama_provider.health_check()
            ollama_status = "healthy" if healthy else "unhealthy"
        except Exception:
            ollama_status = "error"

    # Check model statuses
    model_statuses = await registry.check_model_status()

    return ServiceStatusResponse(
        backend="healthy",
        ollama=ollama_status,
        models=model_statuses,
        sovereign_mode=True,
    )
