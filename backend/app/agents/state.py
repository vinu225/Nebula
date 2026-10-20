"""
Sovereign AI Workbench — LangGraph Agent State Definition

State definition for the agentic execution workflow.
Uses TypedDict and LangChain message reducers.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class PlanStep(TypedDict):
    """Structured representation of a sub-task step in the execution plan."""
    step_index: int
    description: str
    tool_name: Optional[str]
    status: str  # pending, in_progress, completed, failed
    result: Optional[str]
    error: Optional[str]


class AgentState(TypedDict):
    """LangGraph state maintained across the lifecycle of an agent execution."""

    # Chat history with standard LangChain reducer
    messages: Annotated[List[BaseMessage], add_messages]

    # Session & Task tracking
    session_id: str
    task_id: str
    user_query: str

    # Agent planning & execution
    task_category: str
    selected_skill: Optional[str]
    selected_model: Optional[str]
    task_plan: List[PlanStep]
    current_step: int

    # Results & outputs
    tool_results: Dict[str, Any]
    artifacts: List[Dict[str, Any]]
    uploaded_files: List[Dict[str, Any]]
    generated_code: Optional[str]
    generated_code_full: Optional[str]
    generated_artifact_name: Optional[str]
    generated_language: Optional[str]
    vision_analysis: Optional[str]
    vlm_image_data: Optional[Dict[str, Any]]

    # Document pipeline: extracted text & metadata from uploaded files
    document_text: Optional[str]
    document_meta: Optional[Dict[str, Any]]

    # Real-time event log / audit trail
    audit_trail: List[Dict[str, Any]]
    error: Optional[str]
    final_response: Optional[str]
    stream_queue: Optional[Any]
    streamed_to_user: Optional[bool]
