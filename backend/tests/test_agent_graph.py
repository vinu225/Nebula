"""
Unit tests for LangGraph Agent Graph execution.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from app.agents.graph import compiled_agent_graph
from app.storage.database import init_db


@pytest.mark.asyncio
async def test_agent_graph_execution() -> None:
    await init_db()
    initial_state = {
        "messages": [HumanMessage(content="Analyze inspection report and draft approval note")],
        "session_id": "test-session-001",
        "task_id": "task-001",
        "user_query": "Analyze inspection report and draft approval note",
        "task_category": "document",
        "selected_skill": None,
        "selected_model": None,
        "task_plan": [],
        "current_step": 0,
        "tool_results": {},
        "artifacts": [],
        "uploaded_files": [],
        "audit_trail": [],
        "error": None,
        "final_response": None,
    }

    final_state = await compiled_agent_graph.ainvoke(initial_state)

    assert final_state["final_response"] is not None
    assert len(final_state["task_plan"]) > 0
    assert all(step["status"] == "completed" for step in final_state["task_plan"])
    assert len(final_state["audit_trail"]) > 0
    assert "Industrial Task Completed" in final_state["final_response"]
