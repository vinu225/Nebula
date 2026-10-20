"""
Sovereign AI Workbench — Skills API

Endpoints to list and inspect dynamically discovered industrial skills.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from app.skills.registry import SkillRegistry

router = APIRouter(prefix="/api/skills", tags=["skills"])
_skill_registry = SkillRegistry()


@router.get("", response_model=List[Dict[str, Any]])
async def list_skills() -> List[Dict[str, Any]]:
    """List all registered industrial domain skills."""
    skills = _skill_registry.list_skills()
    return [
        {
            "name": s.name,
            "description": s.description,
            "purpose": s.purpose,
            "required_capabilities": s.required_capabilities,
            "required_tools": s.required_tools,
            "expected_outputs": s.expected_outputs,
        }
        for s in skills
    ]
