"""
Sovereign AI Workbench — Multimodal Vision Processing Tool

Prepares images, diagrams, and P&ID drawings for Qwen3-VL inference.
Handles base64 encoding, downscaling high-res engineering scans safely,
and parsing visual inspection inputs.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any, Dict

from PIL import Image
from app.core.logging import get_logger

logger = get_logger(__name__)


def prepare_image_for_vlm(image_input: str | Path | bytes, max_dim: int = 2048) -> Dict[str, Any]:
    """Load, optimize, and base64-encode an image for local vision models.

    Args:
        image_input: File path or raw image bytes.
        max_dim: Max width or height constraint.

    Returns:
        Dict with base64 string, mime type, and dimensions.
    """
    if isinstance(image_input, (str, Path)):
        img = Image.open(str(image_input))
        mime = "image/png" if str(image_input).lower().endswith(".png") else "image/jpeg"
    else:
        img = Image.open(io.BytesIO(image_input))
        mime = "image/png"

    # Convert RGBA to RGB if saving to JPEG
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    width, height = img.size
    if max(width, height) > max_dim:
        scale = max_dim / max(width, height)
        new_size = (int(width * scale), int(height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        width, height = new_size

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")

    logger.info("vlm_image_prepared", width=width, height=height, size_kb=len(buf.getvalue()) // 1024)
    return {
        "base64": b64_str,
        "mime_type": "image/jpeg",
        "width": width,
        "height": height,
    }


def get_pid_analysis_prompt() -> str:
    """Standardized prompt for P&ID diagram inspection with Qwen3-VL."""
    return (
        "You are an expert refinery piping & instrumentation engineer. "
        "Examine the attached P&ID drawing carefully:\n"
        "1. Identify and list all equipment tags (columns, vessels, exchangers, pumps).\n"
        "2. Extract instrument loops and tags (PT, TT, FT, LT, PCV, TCV, FCV, LCV).\n"
        "3. Highlight safety-critical devices: PSVs, rupture discs, emergency shutdown interlocks.\n"
        "4. Trace primary flow streams and note line size/material specs.\n"
        "5. Note any apparent HAZOP concerns or anomalies."
    )
