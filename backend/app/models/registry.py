"""
Sovereign AI Workbench — Model Registry

Central registry for all local models. Models are registered with their metadata
and capabilities. The registry supports dynamic addition of new models.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.models.base import ModelInfo, ModelProvider
from app.models.capabilities import ModelCapability

logger = get_logger(__name__)


class ModelRegistry:
    """Registry of all available local models and their providers.

    The registry maps model names to their metadata and provider instances.
    It supports capability-based lookup for the Model Router.
    """

    def __init__(self) -> None:
        self._models: dict[str, ModelInfo] = {}
        self._providers: dict[str, ModelProvider] = {}  # provider_name -> provider

    def register_provider(self, name: str, provider: ModelProvider) -> None:
        """Register a model inference provider (e.g., Ollama, vLLM).

        Args:
            name: Provider identifier.
            provider: Provider instance.
        """
        self._providers[name] = provider
        logger.info("model_provider_registered", provider=name)

    def get_provider(self, name: str) -> ModelProvider | None:
        """Get a provider by name."""
        return self._providers.get(name)

    def register_model(self, model: ModelInfo) -> None:
        """Register a model with its metadata.

        Args:
            model: Model metadata including capabilities.
        """
        self._models[model.name] = model
        logger.info(
            "model_registered",
            model=model.name,
            provider=model.provider,
            capabilities=[c.value for c in model.capabilities],
        )

    def get_model(self, name: str) -> ModelInfo | None:
        """Get model metadata by name.

        Args:
            name: Model name (e.g., 'qwen3:8b').

        Returns:
            ModelInfo if found, None otherwise.
        """
        return self._models.get(name)

    def list_models(self, enabled_only: bool = True) -> list[ModelInfo]:
        """List all registered models.

        Args:
            enabled_only: If True, only return enabled models.

        Returns:
            List of ModelInfo objects.
        """
        models = list(self._models.values())
        if enabled_only:
            models = [m for m in models if m.enabled]
        return sorted(models, key=lambda m: m.priority)

    def get_models_by_capability(
        self,
        capability: ModelCapability,
        enabled_only: bool = True,
    ) -> list[ModelInfo]:
        """Find models that have a specific capability.

        Args:
            capability: Required capability.
            enabled_only: If True, only return enabled models.

        Returns:
            List of matching ModelInfo objects, sorted by priority.
        """
        models = [
            m for m in self._models.values()
            if m.has_capability(capability) and (not enabled_only or m.enabled)
        ]
        return sorted(models, key=lambda m: m.priority)

    def get_best_model_for_capabilities(
        self,
        capabilities: list[ModelCapability],
        enabled_only: bool = True,
    ) -> ModelInfo | None:
        """Find the best model that satisfies all required capabilities.

        Args:
            capabilities: List of required capabilities.
            enabled_only: If True, only consider enabled models.

        Returns:
            Best matching ModelInfo (lowest priority number = highest priority),
            or None if no model matches.
        """
        candidates = [
            m for m in self._models.values()
            if m.has_all_capabilities(capabilities) and (not enabled_only or m.enabled)
        ]
        if not candidates:
            # Fallback: find model with most matching capabilities
            candidates = list(self._models.values())
            if enabled_only:
                candidates = [m for m in candidates if m.enabled]
            candidates.sort(
                key=lambda m: (
                    -sum(1 for c in capabilities if m.has_capability(c)),
                    m.priority,
                ),
            )
            return candidates[0] if candidates else None

        candidates.sort(key=lambda m: m.priority)
        return candidates[0]

    def get_provider_for_model(self, model_name: str) -> ModelProvider | None:
        """Get the provider instance for a specific model.

        Args:
            model_name: Model name.

        Returns:
            ModelProvider instance, or None if model/provider not found.
        """
        model = self._models.get(model_name)
        if model is None:
            return None
        return self._providers.get(model.provider)

    async def check_model_status(self) -> dict[str, dict]:
        """Check the availability status of all registered models.

        Returns:
            Dict mapping model names to their status info.
        """
        statuses = {}
        for name, model in self._models.items():
            provider = self._providers.get(model.provider)
            if provider is None:
                statuses[name] = {"status": "no_provider", "ready": False}
                continue
            try:
                available = await provider.is_model_available(name)
                statuses[name] = {
                    "status": "ready" if available else "not_loaded",
                    "ready": available,
                    "provider": model.provider,
                    "capabilities": [c.value for c in model.capabilities],
                }
            except Exception as e:
                statuses[name] = {
                    "status": "error",
                    "ready": False,
                    "error": str(e),
                }
        return statuses


def create_default_registry() -> ModelRegistry:
    """Create a ModelRegistry pre-populated with the four Qwen models.

    The actual provider instances are NOT created here — they must be
    registered separately during application startup.

    Returns:
        ModelRegistry with model metadata registered.
    """
    registry = ModelRegistry()

    # --- Qwen3.5:4B — Fast, lightweight chat model ---
    registry.register_model(ModelInfo(
        name="qwen3.5:4b",
        provider="ollama",
        display_name="Qwen 3.5 4B",
        capabilities=[
            ModelCapability.CHAT,
        ],
        context_length=32768,
        vision_support=False,
        coding_support=False,
        reasoning_support=False,
        priority=10,  # Highest priority for simple tasks
        enabled=True,
    ))

    # --- Qwen3:8B — Reasoning model ---
    registry.register_model(ModelInfo(
        name="qwen3:8b",
        provider="ollama",
        display_name="Qwen 3 8B",
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.REASONING,
            ModelCapability.FUNCTION_CALLING,
        ],
        context_length=32768,
        vision_support=False,
        coding_support=False,
        reasoning_support=True,
        priority=30,
        enabled=True,
    ))

    # --- Qwen3-VL:8B — Vision/Multimodal model ---
    registry.register_model(ModelInfo(
        name="qwen3-vl:8b",
        provider="ollama",
        display_name="Qwen 3 VL 8B",
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.VISION,
            ModelCapability.REASONING,
        ],
        context_length=32768,
        vision_support=True,
        coding_support=False,
        reasoning_support=True,
        priority=40,
        enabled=True,
    ))

    # --- Qwen2.5-Coder:8B / latest — Coding model ---
    for model_tag in ["qwen2.5-coder:8b", "qwen2.5-coder:latest"]:
        registry.register_model(ModelInfo(
            name=model_tag,
            provider="ollama",
            display_name="Qwen 2.5 Coder 8B",
            capabilities=[
                ModelCapability.CHAT,
                ModelCapability.CODING,
                ModelCapability.FUNCTION_CALLING,
            ],
            context_length=32768,
            vision_support=False,
            coding_support=True,
            reasoning_support=False,
            priority=25 if "8b" in model_tag else 30,
            enabled=True,
        ))

    # Register default Ollama provider
    try:
        from app.models.ollama import OllamaProvider
        registry.register_provider("ollama", OllamaProvider())
    except Exception as e:
        logger.warning("default_ollama_provider_init_failed", error=str(e))

    return registry
