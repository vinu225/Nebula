"""
Sovereign AI Workbench — Local Embeddings

Generates dense vector representations using local Ollama nomic-embed-text
or internal deterministic vectors if Ollama is unavailable.
"""

from __future__ import annotations

import hashlib
import math
from typing import List

import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _deterministic_mock_embedding(text: str, dim: int = 768) -> List[float]:
    """Fallback deterministic pseudovector based on hash for testing."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    for i in range(dim):
        byte_val = h[i % len(h)]
        vec.append(float((byte_val - 128) / 128.0))
    # Normalize vector to unit length
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


async def get_embedding(text: str) -> List[float]:
    """Obtain dense embedding vector for a piece of text."""
    dim = settings.embedding_dimensions
    url = f"{settings.ollama_base_url}/api/embeddings"
    payload = {
        "model": settings.embedding_model,
        "prompt": text,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                emb = data.get("embedding", [])
                if emb:
                    return emb
    except Exception as e:
        logger.debug("ollama_embedding_unavailable_fallback", reason=str(e))

    return _deterministic_mock_embedding(text, dim=dim)


async def get_batch_embeddings(texts: List[str]) -> List[List[float]]:
    """Compute embeddings for multiple text snippets."""
    return [await get_embedding(t) for t in texts]
