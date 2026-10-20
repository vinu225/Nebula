"""
Sovereign AI Workbench — Hybrid Retrieval (Dense Vector + BM25 RRF)

Queries document chunks via pgvector cosine distance and keyword matching,
fusing scores via Reciprocal Rank Fusion (RRF).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.embeddings import get_embedding
from app.storage.database import get_db_context
from app.storage.models import DocumentChunkModel, DocumentModel

logger = get_logger(__name__)
settings = get_settings()


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def hybrid_search(
    query: str,
    top_k: int = 5,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Execute hybrid dense + sparse retrieval.

    Args:
        query: User search string or question.
        top_k: Max results to return.
        session_id: Optional filter for session-specific files.

    Returns:
        List of matching document chunks sorted by relevance.
    """
    query_vec = await get_embedding(query)
    query_tokens = set(query.lower().split())

    async with get_db_context() as db:
        stmt = (
            select(
                DocumentChunkModel.id,
                DocumentChunkModel.content,
                DocumentChunkModel.page_number,
                DocumentChunkModel.embedding,
                DocumentModel.filename,
                DocumentModel.id.label("document_id"),
            )
            .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
        )
        if session_id:
            stmt = stmt.where(DocumentModel.session_id == session_id)

        rows = (await db.execute(stmt)).all()

    if not rows:
        return []

    # 1. Dense scoring
    dense_scores = []
    # 2. Sparse (keyword match overlap) scoring
    sparse_scores = []

    for r in rows:
        c_id, content, page, emb, filename, doc_id = r
        # Dense similarity
        if emb:
            sim = _cosine_similarity(query_vec, emb)
        else:
            sim = 0.0
        dense_scores.append((c_id, sim, content, page, filename, doc_id))

        # Sparse keyword scoring
        content_tokens = set(content.lower().split())
        match_count = len(query_tokens.intersection(content_tokens))
        sparse_scores.append((c_id, match_count, content, page, filename, doc_id))

    # Rank lists
    dense_ranked = sorted(dense_scores, key=lambda x: x[1], reverse=True)
    sparse_ranked = sorted(sparse_scores, key=lambda x: x[1], reverse=True)

    # Reciprocal Rank Fusion (RRF)
    k = 60
    rrf_scores: Dict[str, float] = {}
    chunk_meta: Dict[str, Any] = {}

    for rank, item in enumerate(dense_ranked):
        cid = item[0]
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank + 1))
        chunk_meta[cid] = item

    for rank, item in enumerate(sparse_ranked):
        cid = item[0]
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank + 1))
        chunk_meta[cid] = item

    fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    results = []
    for cid, score in fused:
        _, _, content, page, filename, doc_id = chunk_meta[cid]
        results.append({
            "chunk_id": cid,
            "document_id": doc_id,
            "filename": filename,
            "page_number": page,
            "content": content,
            "score": round(score, 4),
        })

    logger.info("hybrid_search_executed", query=query, results_count=len(results))
    return results
