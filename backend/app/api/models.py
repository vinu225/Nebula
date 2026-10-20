"""
Sovereign AI Workbench — Model Management API Endpoints

Provides endpoints to:
- Stop/unload models on demand (triggered by UI button or script)
- Check which models are actively in memory (VRAM / RAM)
- Inspect inactivity duration and watchdog status
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services.model_manager import model_manager

logger = get_logger(__name__)
router = APIRouter(prefix="/api/models", tags=["models"])


class StopModelsResponse(BaseModel):
    success: bool
    stopped_models: list[str]
    message: str


class ModelMemoryStatusResponse(BaseModel):
    loaded_models: list[dict[str, Any]]
    count: int
    inactivity_seconds: float
    timeout_seconds: int
    is_active: bool


@router.post("/stop", response_model=StopModelsResponse)
async def stop_models(request: Request) -> StopModelsResponse:
    """Manually stop and unload all loaded models from memory.

    Triggered when user clicks the 'Stop Model' button in the UI.
    Immediately releases GPU VRAM and system memory.
    """
    stopped = await model_manager.stop_all_models(request.app.state)
    logger.info("api_stop_models_called", stopped_models=stopped)
    return StopModelsResponse(
        success=True,
        stopped_models=stopped,
        message=(
            f"Successfully unloaded {len(stopped)} model(s) from memory. GPU/VRAM has been freed."
            if stopped
            else "No models were actively loaded in memory. Memory is already free."
        ),
    )


@router.get("/status", response_model=ModelMemoryStatusResponse)
async def get_model_memory_status(request: Request) -> ModelMemoryStatusResponse:
    """Check which models are currently loaded in VRAM/RAM and current inactivity."""
    loaded = await model_manager.get_loaded_models(request.app.state)
    inactivity = model_manager.get_inactivity_seconds()
    return ModelMemoryStatusResponse(
        loaded_models=loaded,
        count=len(loaded),
        inactivity_seconds=round(inactivity, 1),
        timeout_seconds=model_manager.timeout_seconds,
        is_active=len(loaded) > 0,
    )


@router.post("/touch")
async def touch_activity() -> dict[str, str]:
    """Record user activity to reset the 30-minute inactivity timer."""
    model_manager.record_activity()
    return {"status": "ok", "message": "Inactivity timer reset"}
