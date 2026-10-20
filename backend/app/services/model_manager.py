"""
Sovereign AI Workbench — Model Manager & Inactivity Watchdog

Manages local model lifecycle, tracks user activity, and automatically unloads
models from VRAM / system memory when inactive for 30 minutes.
Also provides manual stop/unload trigger.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Default inactivity timeout: 30 minutes (1800 seconds)
DEFAULT_INACTIVITY_TIMEOUT_SECONDS = 30 * 60

class ModelManager:
    """Manages model memory lifecycle and auto-stops models on inactivity."""

    def __init__(self, timeout_seconds: int = DEFAULT_INACTIVITY_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = timeout_seconds
        self.last_activity_time: float = time.time()
        self._watchdog_task: asyncio.Task | None = None
        self._is_auto_stopped: bool = False

    def record_activity(self) -> None:
        """Update last active timestamp to current time."""
        self.last_activity_time = time.time()
        self._is_auto_stopped = False
        logger.debug("user_activity_recorded", timestamp=self.last_activity_time)

    def get_inactivity_seconds(self) -> float:
        """Return how many seconds since the last user activity."""
        return max(0.0, time.time() - self.last_activity_time)

    async def get_loaded_models(self, app_state: Any) -> list[dict[str, Any]]:
        """List models currently loaded in Ollama VRAM/RAM."""
        registry = getattr(app_state, "model_registry", None)
        if not registry:
            return []
        provider = registry.get_provider("ollama")
        if not provider or not hasattr(provider, "get_loaded_models"):
            return []
        return await provider.get_loaded_models()

    async def stop_all_models(self, app_state: Any) -> list[str]:
        """Manually stop and unload all loaded models from memory."""
        registry = getattr(app_state, "model_registry", None)
        if not registry:
            return []
        provider = registry.get_provider("ollama")
        if not provider or not hasattr(provider, "unload_all_models"):
            return []

        stopped = await provider.unload_all_models()
        self._is_auto_stopped = True
        logger.info("models_manually_stopped", stopped_models=stopped)
        return stopped

    async def _inactivity_watchdog_loop(self, app_state: Any) -> None:
        """Background loop that monitors user inactivity and stops models after timeout."""
        logger.info(
            "inactivity_watchdog_started",
            timeout_minutes=self.timeout_seconds / 60,
        )
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                inactivity = self.get_inactivity_seconds()

                if inactivity >= self.timeout_seconds and not self._is_auto_stopped:
                    loaded = await self.get_loaded_models(app_state)
                    if loaded:
                        model_names = [m.get("name") or m.get("model") for m in loaded]
                        logger.info(
                            "inactivity_threshold_reached",
                            inactivity_minutes=round(inactivity / 60, 1),
                            loaded_models=model_names,
                        )
                        stopped = await self.stop_all_models(app_state)
                        self._is_auto_stopped = True
                        logger.info(
                            "auto_stopped_models_due_to_inactivity",
                            stopped_models=stopped,
                            vram_freed=True,
                        )
                    else:
                        self._is_auto_stopped = True
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("inactivity_watchdog_error", error=str(e))

    def start_watchdog(self, app_state: Any) -> None:
        """Start the background watchdog task."""
        if self._watchdog_task is None or self._watchdog_task.done():
            self._watchdog_task = asyncio.create_task(
                self._inactivity_watchdog_loop(app_state)
            )

    def stop_watchdog(self) -> None:
        """Cancel the background watchdog task."""
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()


# Global singleton
model_manager = ModelManager()
