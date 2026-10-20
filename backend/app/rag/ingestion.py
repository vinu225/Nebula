"""
Sovereign AI Workbench — Document Ingestion Pipeline

Splits documents into semantic chunks, generates local embeddings,
and stores them in PostgreSQL with pgvector for fast retrieval.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.embeddings import get_embedding
from app.storage.database import get_db_context
from app.storage.models import DocumentChunkModel, DocumentModel
from app.tools.pdf import parse_pdf

logger = get_logger(__name__)
settings = get_settings()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Simple robust character/word chunking with overlap."""
    if not text.strip():
        return []

    words = re.split(r"(\s+)", text)
    chunks = []
    current_chunk: List[str] = []
    current_len = 0

    for word in words:
        current_chunk.append(word)
        current_len += len(word)
        if current_len >= chunk_size:
            chunk_str = "".join(current_chunk).strip()
            if chunk_str:
                chunks.append(chunk_str)
            # Retain overlap from end
            overlap_words = []
            overlap_len = 0
            for w in reversed(current_chunk):
                overlap_words.insert(0, w)
                overlap_len += len(w)
                if overlap_len >= overlap:
                    break
            current_chunk = overlap_words
            current_len = overlap_len

    if current_chunk:
        remaining = "".join(current_chunk).strip()
        if remaining:
            chunks.append(remaining)

    return chunks


async def ingest_document(
    file_path: str | Path,
    session_id: Optional[str] = None,
    storage_path: str = "",
) -> Dict[str, Any]:
    """Process, chunk, embed, and index an industrial document."""
    path = Path(file_path)
    file_type = path.suffix.lower().lstrip(".")
    doc_id = str(uuid.uuid4())
    filename = path.name

    from app.tools.unified_document_parser import parse_any_document

    parsed = parse_any_document(path)
    extracted_text = parsed.get("text", "")
    page_count = parsed.get("page_count", 1)
    is_scanned = parsed.get("is_scanned", False)

    chunks = chunk_text(extracted_text, chunk_size=settings.rag_chunk_size, overlap=settings.rag_chunk_overlap)
    # Cap maximum chunks to prevent runaway embedding loops
    if len(chunks) > 50:
        chunks = chunks[:50]

    async with get_db_context() as db:
        doc_record = DocumentModel(
            id=doc_id,
            session_id=session_id,
            filename=filename,
            file_type=file_type,
            storage_path=storage_path or str(path),
            size_bytes=path.stat().st_size if path.exists() else len(extracted_text),
            page_count=page_count,
            is_scanned=is_scanned,
        )
        db.add(doc_record)

        for idx, chunk_content in enumerate(chunks):
            embedding_vec = await get_embedding(chunk_content)
            chunk_record = DocumentChunkModel(
                id=str(uuid.uuid4()),
                document_id=doc_id,
                chunk_index=idx,
                content=chunk_content,
                page_number=1 + (idx * page_count // max(1, len(chunks))),
                token_count=len(chunk_content.split()),
                extra_metadata={"filename": filename, "chunk_index": idx},
                embedding=embedding_vec,
            )
            db.add(chunk_record)

    logger.info("document_ingested", doc_id=doc_id, filename=filename, chunks_count=len(chunks))
    return {
        "document_id": doc_id,
        "filename": filename,
        "chunks_count": len(chunks),
        "page_count": page_count,
        "is_scanned": is_scanned,
    }
