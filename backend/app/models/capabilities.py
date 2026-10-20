"""
Sovereign AI Workbench — Model Capabilities

Defines the capability taxonomy for local models.
Used by the Model Router to select the right model for each task.
"""

from __future__ import annotations

from enum import Enum


class ModelCapability(str, Enum):
    """Capabilities a model can possess."""

    CHAT = "chat"
    REASONING = "reasoning"
    CODING = "coding"
    VISION = "vision"
    EMBEDDING = "embedding"
    FUNCTION_CALLING = "function_calling"


class TaskCategory(str, Enum):
    """High-level task categories identified by the Request Router."""

    CASUAL = "casual"           # Greetings, thanks, simple Q&A
    CONVERSATION = "conversation"  # General conversation
    CODING = "coding"           # Code generation, debugging, testing
    VISION = "vision"           # Image/document understanding
    DOCUMENT = "document"       # Document analysis, report generation
    KNOWLEDGE = "knowledge"     # RAG / knowledge base search
    COMPLEX = "complex"         # Multi-step agentic tasks
    CAD = "cad"                 # 3D CAD modeling, FreeCAD & 2D TechDraw
    DIAGRAM = "diagram"         # Process flow diagrams, schematics & charts


# Mapping from task categories to required model capabilities
TASK_CAPABILITY_MAP: dict[TaskCategory, list[ModelCapability]] = {
    TaskCategory.CASUAL: [ModelCapability.CHAT],
    TaskCategory.CONVERSATION: [ModelCapability.CHAT],
    TaskCategory.CODING: [ModelCapability.CODING],
    TaskCategory.VISION: [ModelCapability.VISION],
    TaskCategory.DOCUMENT: [ModelCapability.REASONING],
    TaskCategory.KNOWLEDGE: [ModelCapability.REASONING],
    TaskCategory.COMPLEX: [ModelCapability.REASONING, ModelCapability.FUNCTION_CALLING],
    TaskCategory.CAD: [ModelCapability.REASONING, ModelCapability.CODING],
    TaskCategory.DIAGRAM: [ModelCapability.REASONING, ModelCapability.CODING],
}
