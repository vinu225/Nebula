"""
Sovereign AI Workbench — PDF Parser Tool

Extracts text, metadata, tables, and renders pages for OCR/vision analysis.
Uses PyMuPDF (fitz) and pdfplumber.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from app.core.logging import get_logger

logger = get_logger(__name__)


def is_pdf_scanned(doc: fitz.Document, min_chars_per_page: int = 50) -> bool:
    """Heuristic check: if pages have virtually no selectable text, it's scanned."""
    total_chars = 0
    pages_to_check = min(len(doc), 5)
    if pages_to_check == 0:
        return False

    for i in range(pages_to_check):
        page = doc[i]
        total_chars += len(page.get_text().strip())

    avg_chars = total_chars / pages_to_check
    return avg_chars < min_chars_per_page


def parse_pdf(file_path: str | Path) -> dict[str, Any]:
    """Parse a PDF document and extract page text and metadata.

    Args:
        file_path: Absolute or local path to PDF file.

    Returns:
        Dict with text, page count, metadata, and is_scanned flag.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        doc = fitz.open(str(path))
        num_pages = len(doc)
        scanned = is_pdf_scanned(doc)

        pages_data = []
        full_text_list = []

        for page_idx in range(num_pages):
            page = doc[page_idx]
            text = page.get_text()
            full_text_list.append(text)
            pages_data.append({
                "page": page_idx + 1,
                "text": text,
                "char_count": len(text.strip()),
            })

        metadata = doc.metadata or {}
        doc.close()

        logger.info("pdf_parsed", path=str(path), pages=num_pages, is_scanned=scanned)
        return {
            "file_name": path.name,
            "page_count": num_pages,
            "is_scanned": scanned,
            "metadata": metadata,
            "text": "\n\n--- PAGE BREAK ---\n\n".join(full_text_list),
            "pages": pages_data,
        }
    except Exception as e:
        logger.error("pdf_parse_failed", path=str(file_path), error=str(e))
        return {"error": str(e)}


def extract_pdf_page_as_image(file_path: str | Path, page_number: int = 1, dpi: int = 200) -> bytes:
    """Render a specific PDF page to PNG image bytes for OCR or Vision."""
    path = Path(file_path)
    doc = fitz.open(str(path))
    if page_number < 1 or page_number > len(doc):
        doc.close()
        raise ValueError(f"Page number {page_number} out of range (1..{len(doc)})")

    page = doc[page_number - 1]
    pix = page.get_pixmap(dpi=dpi)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes
