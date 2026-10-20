"""
Sovereign AI Workbench — Model Router

Selects the best open-weight local model dynamically based on task requirements,
capabilities needed (reasoning, vision, coding, fast chat), and resource availability.
"""

from __future__ import annotations

from typing import Optional

from app.core.logging import get_logger
from app.models.capabilities import ModelCapability, TaskCategory
from app.models.registry import ModelInfo, ModelRegistry

logger = get_logger(__name__)

# Category to primary capabilities mapping
CATEGORY_CAPABILITY_MAP: dict[TaskCategory, list[ModelCapability]] = {
    TaskCategory.CASUAL: [ModelCapability.CHAT],
    TaskCategory.CONVERSATION: [ModelCapability.CHAT],
    TaskCategory.CODING: [ModelCapability.CODING],
    TaskCategory.VISION: [ModelCapability.VISION],
    TaskCategory.DOCUMENT: [ModelCapability.REASONING, ModelCapability.CHAT],
    TaskCategory.KNOWLEDGE: [ModelCapability.REASONING, ModelCapability.CHAT],
    TaskCategory.COMPLEX: [ModelCapability.REASONING, ModelCapability.FUNCTION_CALLING],
    TaskCategory.CAD: [ModelCapability.REASONING],
    TaskCategory.DIAGRAM: [ModelCapability.REASONING],
}


class ModelRouter:
    """Routes requests to the optimal local model without human intervention."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def select_model(
        self,
        category: TaskCategory,
        required_capabilities: Optional[list[ModelCapability]] = None,
        override_model_name: Optional[str] = None,
    ) -> ModelInfo:
        """Select best model for the given task category or requested capabilities.

        Args:
            category: Task category from request router.
            required_capabilities: Specific capabilities required by a skill or sub-task.
            override_model_name: Specific model requested by user if any.

        Returns:
            Selected ModelInfo.
        """
        # 1. User or skill explicit override
        if override_model_name:
            model = self.registry.get_model(override_model_name)
            if model and model.enabled:
                logger.info("model_router_override", model=model.name, requested=override_model_name)
                return model

        # 2. Match based on explicit capabilities if provided
        caps = required_capabilities or CATEGORY_CAPABILITY_MAP.get(category, [ModelCapability.CHAT])

        candidate = self.registry.get_best_model_for_capabilities(caps, enabled_only=True)
        if candidate:
            logger.info(
                "model_router_selected",
                model=candidate.name,
                category=category.value,
                capabilities=[c.value for c in caps],
            )
            return candidate

        # 3. Fallback to default lightweight model
        fallback = self.registry.get_model("qwen3.5:4b") or self.registry.list_models()[0]
        logger.warning("model_router_fallback", model=fallback.name, category=category.value)
        return fallback
