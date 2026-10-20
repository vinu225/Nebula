"""
Sovereign AI Workbench — File Ingestion & Management API

Handles multipart file uploads, local storage persistence,
and triggers automatic document chunking and vector indexing.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.ingestion import ingest_document
from app.storage.database import get_db
from app.storage.models import DocumentModel
from app.storage.object_storage import get_storage_client
from app.services.model_manager import model_manager

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
) -> Dict[str, Any]:
    """Upload an industrial document (PDF, P&ID drawing, DOCX, spreadsheet) and index it."""
    model_manager.record_activity()
    storage = get_storage_client()
    contents = await file.read()
    filename = file.filename or f"upload_{uuid.uuid4().hex[:8]}"

    # Save to storage
    object_name = f"{session_id or 'global'}/{uuid.uuid4().hex[:6]}_{filename}"
    storage_path = await storage.upload_file(
        bucket=settings.minio_bucket_uploads,
        object_name=object_name,
        data=contents,
        content_type=file.content_type or "application/octet-stream",
    )

    # Obtain disk path for local parsers
    local_path = await storage.get_local_path(
        bucket=settings.minio_bucket_uploads,
        object_name=object_name,
    )

    # Ingest and embed document
    ingest_result = await ingest_document(
        file_path=local_path,
        session_id=session_id,
        storage_path=storage_path,
    )

    return {
        "status": "success",
        "file_name": filename,
        "document_id": ingest_result.get("document_id"),
        "chunks_indexed": ingest_result.get("chunks_count", 0),
        "page_count": ingest_result.get("page_count", 1),
        "is_scanned": ingest_result.get("is_scanned", False),
        "storage_path": storage_path,
    }


@router.get("", response_model=List[Dict[str, Any]])
async def list_files(
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List indexed documents."""
    stmt = select(DocumentModel).order_by(desc(DocumentModel.created_at))
    if session_id:
        stmt = stmt.where(DocumentModel.session_id == session_id)

    res = await db.execute(stmt)
    docs = res.scalars().all()

    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "size_bytes": d.size_bytes,
            "page_count": d.page_count,
            "is_scanned": d.is_scanned,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


from pydantic import BaseModel, Field


class FileItem(BaseModel):
    filename: str
    content: str


class WriteProjectPayload(BaseModel):
    folder_name: str = Field(..., description="Project folder name")
    files: List[FileItem]


@router.post("/write-project")
async def write_project_files(payload: WriteProjectPayload) -> Dict[str, Any]:
    """Mini-Antigravity file and folder creator.
    
    Creates a project folder inside the workspace and writes the generated
    files securely after user confirmation in the UI.
    """
    from pathlib import Path
    import re

    # Sanitize folder name
    clean_folder = re.sub(r'[^a-zA-Z0-9_\-]', '_', payload.folder_name.strip())
    if not clean_folder:
        clean_folder = f"project_{uuid.uuid4().hex[:6]}"

    target_dir = (settings.workspace_dir / "projects" / clean_folder).resolve()

    # Safety check against path traversal
    try:
        target_dir.relative_to(settings.workspace_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid target directory path")

    target_dir.mkdir(parents=True, exist_ok=True)

    written_files: List[Dict[str, Any]] = []
    has_html = False

    for item in payload.files:
        clean_filename = Path(item.filename).name  # prevent directory traversal in filename
        if not clean_filename:
            continue

        file_path = target_dir / clean_filename
        file_path.write_text(item.content, encoding="utf-8")
        written_files.append({
            "filename": clean_filename,
            "path": str(file_path),
            "size": len(item.content.encode("utf-8")),
        })

        if clean_filename.lower().endswith(".html"):
            has_html = True
            # Also copy to frontend public folder for instant live browser preview
            try:
                public_preview = settings.base_dir.parent / "frontend" / "public" / f"preview_{clean_folder}.html"
                public_preview.write_text(item.content, encoding="utf-8")
            except Exception as e:
                logger.warning("public_preview_copy_failed", error=str(e))

    preview_url = f"http://localhost:3000/preview_{clean_folder}.html" if has_html else None

    logger.info(
        "project_files_written",
        folder=clean_folder,
        files_count=len(written_files),
        target_dir=str(target_dir),
    )

    return {
        "status": "success",
        "message": f"Successfully created folder '{clean_folder}' and {len(written_files)} file(s).",
        "folder_name": clean_folder,
        "target_dir": str(target_dir),
        "files": written_files,
        "preview_url": preview_url,
    }
