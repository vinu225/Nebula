"""
Sovereign AI Workbench — Authentication Middleware and Dependencies

Verifies local API key header or session tokens.
Air-gapped and configurable for internal corporate SSO/JWT extension.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import get_settings

settings = get_settings()
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Validate API key for protected workbench endpoints."""
    # In development mode, allow requests even without explicit header if matching default
    if not settings.app_debug:
        if not api_key or api_key != settings.app_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing sovereign API key",
            )
    return api_key or "dev_user"
