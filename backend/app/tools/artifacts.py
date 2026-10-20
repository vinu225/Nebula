"""
Sovereign AI Workbench — Artifact Management Tool

Tracks generated output files (word docs, spreadsheets, code, diagrams)
persisting them to storage and cataloging them in the database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.storage.database import get_db_context
from app.storage.models import ArtifactModel
from app.storage.object_storage import get_storage_client

logger = get_logger(__name__)
settings = get_settings()


async def save_artifact(
    session_id: str,
    name: str,
    file_type: str,
    data: bytes,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Store generated artifact to MinIO/local storage and log to DB.

    Args:
        session_id: The session this artifact belongs to.
        name: Filename (e.g. 'MRPL_Approval_Note_V101.docx').
        file_type: Extension or MIME category (docx, pptx, xlsx, py, pdf).
        data: Raw binary content.
        extra_metadata: Additional context tags.

    Returns:
        Dict with artifact details and download link.
    """
    artifact_id = str(uuid.uuid4())
    object_name = f"{session_id}/{artifact_id}_{name}"
    storage = get_storage_client()

    content_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
        "py": "text/x-python",
        "png": "image/png",
        "svg": "image/svg+xml",
        "dxf": "application/dxf",
        "stl": "model/stl",
        "fcstd": "application/x-freecad",
    }
    c_type = content_types.get(file_type.lower(), "application/octet-stream")

    storage_path = await storage.upload_file(
        bucket=settings.minio_bucket_artifacts,
        object_name=object_name,
        data=data,
        content_type=c_type,
    )

    meta = extra_metadata or {}
    meta["original_name"] = name
    meta["object_name"] = object_name

    async with get_db_context() as db:
        art_record = ArtifactModel(
            id=artifact_id,
            session_id=session_id,
            name=name,
            file_type=file_type.lower(),
            storage_path=storage_path,
            size_bytes=len(data),
            extra_metadata=meta,
            created_at=datetime.now(timezone.utc),
        )
        db.add(art_record)

    logger.info("artifact_saved", artifact_id=artifact_id, name=name, size=len(data))
    return {
        "artifact_id": artifact_id,
        "name": name,
        "file_type": file_type.lower(),
        "size_bytes": len(data),
        "storage_path": storage_path,
        "download_url": f"/api/artifacts/{artifact_id}/download",
    }
