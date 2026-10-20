"""
Unit tests for ModelRouter.
"""

from __future__ import annotations

import pytest

from app.models.capabilities import ModelCapability, TaskCategory
from app.models.registry import create_default_registry
from app.routing.model_router import ModelRouter


@pytest.fixture
def router() -> ModelRouter:
    registry = create_default_registry()
    return ModelRouter(registry)


def test_select_coding_model(router: ModelRouter) -> None:
    model = router.select_model(TaskCategory.CODING)
    assert model.name == "qwen2.5-coder:8b"
    assert model.coding_support is True


def test_select_vision_model(router: ModelRouter) -> None:
    model = router.select_model(TaskCategory.VISION)
    assert model.name == "qwen3-vl:8b"
    assert model.vision_support is True


def test_select_reasoning_model(router: ModelRouter) -> None:
    model = router.select_model(TaskCategory.COMPLEX)
    assert model.name in ("qwen3:8b", "qwen3-vl:8b")


def test_select_casual_model(router: ModelRouter) -> None:
    model = router.select_model(TaskCategory.CASUAL)
    assert model.name == "qwen3.5:4b"


def test_select_with_override(router: ModelRouter) -> None:
    model = router.select_model(TaskCategory.CASUAL, override_model_name="qwen2.5-coder:8b")
    assert model.name == "qwen2.5-coder:8b"
