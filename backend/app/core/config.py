"""
Sovereign AI Workbench — Configuration Module

All configuration is loaded from environment variables / .env file.
Centralized Pydantic Settings class for the entire application.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "MRPL AI Workbench"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_api_key: str = "sovereign-dev-key-change-in-production"

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: int = 120

    # --- PostgreSQL ---
    database_url: str = (
        "postgresql+asyncpg://sovereign:sovereign@localhost:5432/sovereign_workbench"
    )
    database_sync_url: str = (
        "postgresql://sovereign:sovereign@localhost:5432/sovereign_workbench"
    )

    # --- MinIO ---
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket_uploads: str = "uploads"
    minio_bucket_documents: str = "documents"
    minio_bucket_artifacts: str = "artifacts"
    minio_bucket_sandbox: str = "sandbox"

    # --- Docker Sandbox ---
    sandbox_image: str = "sovereign-sandbox:latest"
    sandbox_timeout: int = 30
    sandbox_memory_limit: str = "256m"
    sandbox_cpu_limit: float = 1.0
    sandbox_network_disabled: bool = True

    # --- RAG / Embeddings ---
    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 50
    rag_top_k: int = 5

    # --- Security ---
    sovereign_mode: bool = True
    block_external_network: bool = True

    # --- Logging ---
    log_level: str = "INFO"
    log_format: str = "json"

    # --- Derived paths ---
    @property
    def workspace_dir(self) -> Path:
        """Root workspace directory for file operations."""
        workspace = Path(__file__).resolve().parent.parent.parent / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    @property
    def skills_dir(self) -> Path:
        """Skills definitions directory."""
        root_skills = Path(__file__).resolve().parent.parent.parent.parent / "skills"
        if root_skills.exists():
            return root_skills
        return Path(__file__).resolve().parent.parent.parent / "skills"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
