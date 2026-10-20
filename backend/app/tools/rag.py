"""
Sovereign AI Workbench — RAG Search Tool

Callable tool for the agent to retrieve factual context from internal documents.
"""

from __future__ import annotations

from typing import Optional
from app.rag.reranker import rerank_results
from app.rag.retrieval import hybrid_search


async def search_knowledge_base(query: str, session_id: Optional[str] = None, top_k: int = 4) -> str:
    """Search internal refinery manuals, SOPs, and inspection history.

    Args:
        query: Search query or technical question.
        session_id: Optional session identifier.
        top_k: Number of relevant snippets to return.

    Returns:
        Formatted context string with citations.
    """
    candidates = await hybrid_search(query=query, top_k=top_k * 2, session_id=session_id)
    reranked = rerank_results(query=query, candidates=candidates, max_results=top_k)

    if not reranked:
        return "No relevant internal documentation found in the local knowledge base."

    snippets = []
    for idx, r in enumerate(reranked, start=1):
        snippets.append(
            f"[{idx}] Source: {r['filename']} (Page {r.get('page_number', 'N/A')})\n{r['content']}"
        )

    return "\n\n---\n\n".join(snippets)
