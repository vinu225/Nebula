"""
Sovereign AI Workbench — Skill Loader

Loads and parses skill directories containing metadata.json and skill.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SkillDefinition:
    """Represents a loaded skill definition."""
    name: str
    description: str
    purpose: str
    required_capabilities: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    instructions: str = ""
    extra_metadata: dict[str, Any] = field(default_factory=dict)


def load_skill_from_dir(skill_dir: Path) -> SkillDefinition | None:
    """Load a single skill directory containing metadata.json and skill.md."""
    metadata_path = skill_dir / "metadata.json"
    skill_md_path = skill_dir / "skill.md"

    if not metadata_path.exists():
        logger.warning("skill_missing_metadata", path=str(skill_dir))
        return None

    try:
        with open(metadata_path, encoding="utf-8") as f:
            meta = json.load(f)

        instructions = ""
        if skill_md_path.exists():
            with open(skill_md_path, encoding="utf-8") as f:
                instructions = f.read()

        skill = SkillDefinition(
            name=meta.get("name", skill_dir.name),
            description=meta.get("description", ""),
            purpose=meta.get("purpose", ""),
            required_capabilities=meta.get("required_capabilities", []),
            required_tools=meta.get("required_tools", []),
            expected_outputs=meta.get("expected_outputs", []),
            instructions=instructions,
            extra_metadata=meta,
        )
        logger.info("skill_loaded", skill=skill.name, path=str(skill_dir))
        return skill
    except Exception as e:
        logger.error("skill_load_failed", path=str(skill_dir), error=str(e))
        return None
