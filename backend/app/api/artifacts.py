"""
Sovereign AI Workbench — Artifact Download API

Provides endpoints for listing and downloading generated output files
(Word approval notes, Excel models, PPT decks, PDFs, and scripts).
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.storage.database import get_db
from app.storage.models import ArtifactModel
from app.storage.object_storage import get_storage_client

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])
settings = get_settings()


@router.get("", response_model=List[Dict[str, Any]])
async def list_artifacts(
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List generated artifacts."""
    stmt = select(ArtifactModel).order_by(desc(ArtifactModel.created_at))
    if session_id:
        stmt = stmt.where(ArtifactModel.session_id == session_id)

    res = await db.execute(stmt)
    artifacts = res.scalars().all()

    return [
        {
            "id": a.id,
            "session_id": a.session_id,
            "name": a.name,
            "file_type": a.file_type,
            "size_bytes": a.size_bytes,
            "download_url": f"/api/artifacts/{a.id}/download",
            "created_at": a.created_at.isoformat(),
        }
        for a in artifacts
    ]


@router.get("/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download artifact as binary attachment."""
    stmt = select(ArtifactModel).where(ArtifactModel.id == artifact_id)
    res = await db.execute(stmt)
    art = res.scalar_one_or_none()

    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")

    storage = get_storage_client()
    object_name = art.extra_metadata.get("object_name") if art.extra_metadata else None
    if not object_name:
        object_name = f"{art.session_id}/{art.id}_{art.name}"

    try:
        data = await storage.download_file(
            bucket=settings.minio_bucket_artifacts,
            object_name=object_name,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found in storage: {str(e)}")

    mime_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
        "py": "text/x-python",
        "png": "image/png",
    }
    media_type = mime_types.get(art.file_type.lower(), "application/octet-stream")

    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{art.name}"',
        },
    )


@router.delete("/{artifact_id}")
async def delete_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Delete an artifact by ID from the database."""
    stmt = select(ArtifactModel).where(ArtifactModel.id == artifact_id)
    res = await db.execute(stmt)
    art = res.scalar_one_or_none()
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")

    await db.delete(art)
    await db.commit()
    return {"status": "success", "message": f"Artifact {artifact_id} deleted"}


@router.delete("")
async def clear_all_artifacts(
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Clear all artifacts or artifacts for a specific session."""
    from sqlalchemy import delete
    stmt = delete(ArtifactModel)
    if session_id:
        stmt = stmt.where(ArtifactModel.session_id == session_id)
    result = await db.execute(stmt)
    await db.commit()
    return {"status": "success", "cleared": result.rowcount}

