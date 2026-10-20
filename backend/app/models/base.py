"""
Sovereign AI Workbench — Abstract Model Provider

Defines the interface that all model providers (Ollama, vLLM, etc.) must implement.
This abstraction allows swapping inference backends without changing agent logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from app.models.capabilities import ModelCapability


@dataclass
class ModelInfo:
    """Metadata for a registered model."""

    name: str                       # e.g., "qwen3:8b"
    provider: str                   # e.g., "ollama"
    display_name: str               # e.g., "Qwen3 8B"
    capabilities: list[ModelCapability] = field(default_factory=list)
    context_length: int = 8192
    vision_support: bool = False
    coding_support: bool = False
    reasoning_support: bool = False
    priority: int = 50              # Lower = higher priority (0 = highest)
    enabled: bool = True
    parameters: dict[str, Any] = field(default_factory=dict)

    def has_capability(self, capability: ModelCapability) -> bool:
        """Check if this model has a specific capability."""
        return capability in self.capabilities

    def has_all_capabilities(self, capabilities: list[ModelCapability]) -> bool:
        """Check if this model has all specified capabilities."""
        return all(c in self.capabilities for c in capabilities)


@dataclass
class GenerationResult:
    """Result from a model generation call."""

    content: str
    model: str
    finish_reason: str | None = None
    usage: dict[str, int] | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ModelProvider(ABC):
    """Abstract base class for model inference providers.

    Implementations: OllamaProvider, (future) VLLMProvider, etc.
    """

    @abstractmethod
    async def generate(
        self,
        model_name: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate a response from the model.

        Args:
            model_name: Name of the model to use.
            messages: Chat messages in OpenAI-compatible format.
            **kwargs: Additional provider-specific parameters.

        Returns:
            GenerationResult with the model's response.
        """
        ...

    @abstractmethod
    async def stream(
        self,
        model_name: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a response token-by-token.

        Args:
            model_name: Name of the model to use.
            messages: Chat messages in OpenAI-compatible format.
            **kwargs: Additional provider-specific parameters.

        Yields:
            Individual tokens as they are generated.
        """
        ...

    @abstractmethod
    async def is_model_available(self, model_name: str) -> bool:
        """Check if a specific model is available and ready.

        Args:
            model_name: Name of the model to check.

        Returns:
            True if the model is loaded and ready for inference.
        """
        ...

    @abstractmethod
    async def list_available_models(self) -> list[str]:
        """List all models currently available on this provider.

        Returns:
            List of model name strings.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider service is healthy and reachable.

        Returns:
            True if the provider is healthy.
        """
        ...
