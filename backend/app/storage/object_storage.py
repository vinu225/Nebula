"""
Sovereign AI Workbench — Object Storage (MinIO / Local Fallback)

Provides air-gapped file storage for uploaded documents, generated artifacts,
and sandbox workspaces.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import BinaryIO, Optional

import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class StorageClient:
    """Storage client managing buckets for uploads, documents, and artifacts."""

    def __init__(self) -> None:
        self.minio_client = None
        self.local_storage_dir = settings.workspace_dir / "storage"
        self.local_storage_dir.mkdir(parents=True, exist_ok=True)
        self._init_client()

    def _init_client(self) -> None:
        import socket
        try:
            parts = settings.minio_endpoint.split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 9000
            sock = socket.create_connection((host, port), timeout=0.2)
            sock.close()

            from minio import Minio
            self.minio_client = Minio(
                endpoint=settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            # Ensure default buckets exist
            for bucket in [
                settings.minio_bucket_uploads,
                settings.minio_bucket_documents,
                settings.minio_bucket_artifacts,
                settings.minio_bucket_sandbox,
            ]:
                if not self.minio_client.bucket_exists(bucket):
                    self.minio_client.make_bucket(bucket)
            logger.info("minio_storage_initialized", endpoint=settings.minio_endpoint)
        except Exception as e:
            logger.warning(
                "minio_storage_unavailable_using_local_fs",
                reason=str(e),
                local_dir=str(self.local_storage_dir),
            )
            self.minio_client = None

    async def upload_file(
        self,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file bytes to bucket or local directory."""
        if self.minio_client:
            import io
            def _upload() -> None:
                stream = io.BytesIO(data)
                self.minio_client.put_object(
                    bucket_name=bucket,
                    object_name=object_name,
                    data=stream,
                    length=len(data),
                    content_type=content_type,
                )
            await asyncio.to_thread(_upload)
            return f"minio://{bucket}/{object_name}"
        else:
            bucket_dir = self.local_storage_dir / bucket
            bucket_dir.mkdir(parents=True, exist_ok=True)
            target = bucket_dir / object_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return f"local://{bucket}/{object_name}"

    async def download_file(self, bucket: str, object_name: str) -> bytes:
        """Download file bytes from bucket or local storage."""
        if self.minio_client:
            def _download() -> bytes:
                response = self.minio_client.get_object(bucket, object_name)
                try:
                    return response.read()
                finally:
                    response.close()
                    response.release_conn()
            return await asyncio.to_thread(_download)
        else:
            target = self.local_storage_dir / bucket / object_name
            if not target.exists():
                raise FileNotFoundError(f"Object {object_name} not found in {bucket}")
            return target.read_bytes()

    async def get_local_path(self, bucket: str, object_name: str) -> Path:
        """Ensure file is available on local disk and return absolute Path."""
        bucket_dir = self.local_storage_dir / bucket
        bucket_dir.mkdir(parents=True, exist_ok=True)
        local_file = bucket_dir / object_name
        local_file.parent.mkdir(parents=True, exist_ok=True)

        if not local_file.exists() and self.minio_client:
            content = await self.download_file(bucket, object_name)
            local_file.write_bytes(content)

        return local_file


# Global singleton
_storage_client: Optional[StorageClient] = None


def get_storage_client() -> StorageClient:
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageClient()
    return _storage_client
