"""
Unit tests for SkillRegistry and SkillLoader.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models.capabilities import TaskCategory
from app.skills.registry import SkillRegistry


@pytest.fixture
def registry() -> SkillRegistry:
    skills_dir = Path(__file__).resolve().parent.parent.parent / "skills"
    return SkillRegistry(skills_dir=skills_dir)


def test_discover_skills(registry: SkillRegistry) -> None:
    skills = registry.list_skills()
    assert len(skills) >= 7
    skill_names = {s.name for s in skills}
    expected = {
        "document_analysis",
        "inspection_report",
        "coding",
        "pid_analysis",
        "knowledge_research",
        "approval_note",
        "spreadsheet_analysis",
    }
    assert expected.issubset(skill_names)


def test_get_skill(registry: SkillRegistry) -> None:
    skill = registry.get_skill("inspection_report")
    assert skill is not None
    assert "inspection" in skill.name
    assert len(skill.instructions) > 0


def test_match_skill_by_query(registry: SkillRegistry) -> None:
    skill = registry.match_skill(TaskCategory.DOCUMENT, "Draft an approval note for this equipment")
    assert skill is not None
    assert skill.name == "approval_note"

    skill_pid = registry.match_skill(TaskCategory.VISION, "Analyze the P&ID diagram and find valves")
    assert skill_pid is not None
    assert skill_pid.name == "pid_analysis"
