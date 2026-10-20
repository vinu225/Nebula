"""
Sovereign AI Workbench — Local OCR Tool

Extracts text from scanned engineering drawings, inspection forms, and photos.
Uses pytesseract and EasyOCR with automatic fallback.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter
from app.core.logging import get_logger

logger = get_logger(__name__)

_easyocr_reader = None


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """Enhance image contrast and sharpness for higher OCR accuracy."""
    # Convert to grayscale
    gray = image.convert("L")
    # Increase contrast
    enhancer = ImageEnhance.Contrast(gray)
    contrasted = enhancer.enhance(1.8)
    # Sharpen slightly
    sharpened = contrasted.filter(ImageFilter.SHARPEN)
    return sharpened


def perform_ocr(
    image_input: str | Path | bytes | Image.Image,
    engine: str = "auto",
) -> dict[str, Any]:
    """Perform local OCR on an image file or bytes.

    Args:
        image_input: File path, raw bytes, or PIL Image.
        engine: 'tesseract', 'easyocr', or 'auto'.

    Returns:
        Dict with extracted text, engine used, and confidence.
    """
    global _easyocr_reader

    # Resolve PIL Image
    if isinstance(image_input, (str, Path)):
        img = Image.open(str(image_input))
    elif isinstance(image_input, bytes):
        img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, Image.Image):
        img = image_input
    else:
        return {"error": "Invalid image input type"}

    processed_img = preprocess_image_for_ocr(img)

    # 1. Try pytesseract first if requested or auto
    if engine in ("tesseract", "auto"):
        try:
            import pytesseract
            text = pytesseract.image_to_string(processed_img)
            if text.strip():
                logger.info("ocr_success_tesseract", char_count=len(text))
                return {
                    "text": text.strip(),
                    "engine": "pytesseract",
                    "success": True,
                }
        except Exception as e:
            logger.debug("pytesseract_failed_or_missing", reason=str(e))

    # 2. Try EasyOCR
    if engine in ("easyocr", "auto"):
        try:
            import easyocr
            import numpy as np
            if _easyocr_reader is None:
                _easyocr_reader = easyocr.Reader(["en"], gpu=False)

            img_np = np.array(processed_img)
            results = _easyocr_reader.readtext(img_np)
            extracted_lines = [res[1] for res in results]
            full_text = "\n".join(extracted_lines)

            logger.info("ocr_success_easyocr", char_count=len(full_text))
            return {
                "text": full_text.strip(),
                "engine": "easyocr",
                "success": True,
            }
        except Exception as e:
            logger.warning("easyocr_failed", error=str(e))

    return {
        "text": "",
        "engine": "none",
        "success": False,
        "error": "No working local OCR engine available (install tesseract or easyocr)",
    }
