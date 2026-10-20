
"""
Unit tests for Native Tools and Document Ingestion.
"""

from __future__ import annotations

import pytest

from app.rag.ingestion import chunk_text
from app.tools.calculator import evaluate_math
from app.tools.documents import (
    generate_approval_note_docx,
    generate_pdf_report,
    generate_presentation_pptx,
    generate_spreadsheet_xlsx,
)


def test_calculator_basic_and_complex() -> None:
    assert evaluate_math("2 + 2") == "4"
    assert evaluate_math("100 * 0.85 / 2") == "42.5"
    assert evaluate_math("sqrt(16) + 10") == "14.0"


def test_calculator_security_blocks_injection() -> None:
    res = evaluate_math("__import__('os').system('echo pwned')")
    assert "Error" in res or "not allowed" in res or "not permitted" in res


def test_generate_approval_note_docx() -> None:
    data = generate_approval_note_docx(
        subject="Repair of Crude Column Overhead Cooler E-101",
        sections=[
            {"title": "Background", "content": "Ultrasonic thickness measurement revealed wall thinning below MRT."},
            {"title": "Proposal", "content": "Procure titanium replacement bundle."},
        ],
    )
    assert len(data) > 1000
    assert data[:4] == b"PK\x03\x04"  # zip header for docx


def test_generate_spreadsheet_xlsx() -> None:
    data = generate_spreadsheet_xlsx(
        sheet_title="Refinery KPIs",
        headers=["Unit", "Design BPD", "Actual BPD", "Variance"],
        rows=[
            ["CDU-1", 120000, 118500, -1500],
            ["VDU-1", 45000, 44200, -800],
        ],
    )
    assert len(data) > 1000
    assert data[:4] == b"PK\x03\x04"  # zip header for xlsx


def test_generate_presentation_pptx() -> None:
    data = generate_presentation_pptx(
        title="Plant Inspection Review",
        slides=[{"title": "Executive Summary", "points": ["Completed 42 equipment inspections", "Zero critical leaks"]}],
    )
    assert len(data) > 1000
    assert data[:4] == b"PK\x03\x04"


def test_generate_pdf_report() -> None:
    data = generate_pdf_report(
        title="Plant Safety Audit Report",
        content_paragraphs=["Audit completed according to OISD-116 standards.", "All interlocks tested OK."],
    )
    assert len(data) > 500
    assert data[:4] == b"%PDF"


def test_chunk_text() -> None:
    sample = "Word " * 200
    chunks = chunk_text(sample, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) > 0 for c in chunks)
