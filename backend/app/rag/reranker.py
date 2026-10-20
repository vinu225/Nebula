"""
Sovereign AI Workbench — Local Document Reranker

Reranks candidate chunks from hybrid retrieval to prioritize highest relevance
clauses, tables, and specifications.
"""

from __future__ import annotations

from typing import Any, Dict, List
from app.core.logging import get_logger

logger = get_logger(__name__)


def rerank_results(query: str, candidates: List[Dict[str, Any]], max_results: int = 5) -> List[Dict[str, Any]]:
    """Rerank candidates based on exact query phrase match and sentence density."""
    if not candidates:
        return []

    q_lower = query.lower()
    scored = []

    for item in candidates:
        content = item.get("content", "").lower()
        base_score = item.get("score", 0.0)

        # Boost if exact phrase or primary nouns are in chunk
        boost = 0.0
        if q_lower in content:
            boost += 0.5

        # Check keyword count
        for term in q_lower.split():
            if len(term) > 3 and term in content:
                boost += 0.1

        total_score = base_score + boost
        item_copy = dict(item)
        item_copy["reranked_score"] = round(total_score, 4)
        scored.append(item_copy)

    scored.sort(key=lambda x: x["reranked_score"], reverse=True)
    return scored[:max_results]
