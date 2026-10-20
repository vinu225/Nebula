"""
Sovereign AI Workbench — Skill Registry

Discovers, registers, and matches skills dynamically from the skills/ directory.
Enables plug-and-play addition of industrial domain skills without code rewrites.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.capabilities import TaskCategory
from app.skills.loader import SkillDefinition, load_skill_from_dir

logger = get_logger(__name__)
settings = get_settings()

CATEGORY_SKILL_HINTS: dict[TaskCategory, list[str]] = {
    TaskCategory.CODING: ["coding"],
    TaskCategory.VISION: ["pid_analysis", "inspection_report"],
    TaskCategory.DOCUMENT: ["document_analysis", "inspection_report", "approval_note", "spreadsheet_analysis"],
    TaskCategory.KNOWLEDGE: ["knowledge_research"],
    TaskCategory.COMPLEX: ["document_analysis", "inspection_report", "approval_note"],
    TaskCategory.CAD: ["cad"],
    TaskCategory.DIAGRAM: ["diagram"],
}


class SkillRegistry:
    """Registry that manages loaded industrial skills."""

    def __init__(self, skills_dir: Optional[Path] = None) -> None:
        self.skills_dir = skills_dir or settings.skills_dir
        self._skills: dict[str, SkillDefinition] = {}
        self.discover_skills()

    def discover_skills(self) -> None:
        """Scan the skills directory and load all skills found."""
        self._skills.clear()
        if not self.skills_dir.exists():
            logger.warning("skills_directory_missing", path=str(self.skills_dir))
            return

        for item in self.skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith((".", "_")):
                skill = load_skill_from_dir(item)
                if skill:
                    self._skills[skill.name] = skill

        logger.info("skills_discovery_complete", count=len(self._skills), loaded=list(self._skills.keys()))

    def register_skill(self, skill: SkillDefinition) -> None:
        """Manually register or override a skill definition."""
        self._skills[skill.name] = skill

    def get_skill(self, name: str) -> SkillDefinition | None:
        """Get a specific skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[SkillDefinition]:
        """List all discovered skills."""
        return list(self._skills.values())

    def match_skill(
        self,
        category: TaskCategory,
        user_query: str,
        explicit_skill_name: Optional[str] = None,
    ) -> SkillDefinition | None:
        """Select the most relevant skill for a task.

        Args:
            category: TaskCategory from request router.
            user_query: The user prompt.
            explicit_skill_name: User or pipeline requested skill name.

        Returns:
            Best matching SkillDefinition or None.
        """
        if explicit_skill_name and explicit_skill_name in self._skills:
            return self._skills[explicit_skill_name]

        query_lower = user_query.lower()

        # Specific query heuristics
        if "approval note" in query_lower:
            if "approval_note" in self._skills:
                return self._skills["approval_note"]

        if any(w in query_lower for w in ["p&id", "pid", "piping", "schematic"]):
            if "pid_analysis" in self._skills:
                return self._skills["pid_analysis"]

        if any(w in query_lower for w in ["inspection", "inspection report", "ndt", "hydrotest"]):
            if "inspection_report" in self._skills:
                return self._skills["inspection_report"]

        if any(w in query_lower for w in ["excel", "sheet", "spreadsheet", "csv", "table", "formula"]):
            if "spreadsheet_analysis" in self._skills:
                return self._skills["spreadsheet_analysis"]

        if category == TaskCategory.CAD or any(w in query_lower for w in ["cad", "freecad", "fcstd", "dxf", "flange", "valve", "drawing", "3d model"]):
            if "cad" in self._skills:
                return self._skills["cad"]

        if any(w in query_lower for w in ["code", "script", "function", "program", "python", "bug"]):
            if "coding" in self._skills:
                return self._skills["coding"]

        if any(w in query_lower for w in ["sop", "procedure", "policy", "standard", "knowledge base"]):
            if "knowledge_research" in self._skills:
                return self._skills["knowledge_research"]

        # Category hints fallback
        hints = CATEGORY_SKILL_HINTS.get(category, [])
        for hint in hints:
            if hint in self._skills:
                return self._skills[hint]

        return self._skills.get("document_analysis") or (self.list_skills()[0] if self._skills else None)
