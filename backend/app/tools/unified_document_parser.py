"""
Sovereign AI Workbench — Unified Document Parser Pipeline

Supports multi-format industrial document extraction:
- Microsoft Word (.docx, .doc) — paragraphs, headings, tables
- Microsoft PowerPoint (.pptx, .ppt) — slides, titles, shapes, notes, tables
- Microsoft Excel (.xlsx, .xls, .csv) — sheets, rows, markdown table formatting
- Portable Document Format (.pdf) — PyMuPDF high-speed parsing & OCR fallback
- Text & Markdown (.txt, .md, .log, .json, .yaml) — multi-encoding robust reader
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Dict, List

from app.core.logging import get_logger
from app.tools.pdf import parse_pdf

logger = get_logger(__name__)


def _docx_table_to_markdown(table) -> str:
    """Convert a python-docx table to a GitHub Flavored Markdown table."""
    rows = []
    for r_idx, row in enumerate(table.rows):
        cells = [c.text.strip().replace("\n", " ") for c in row.cells]
        rows.append(f"| {' | '.join(cells)} |")
        if r_idx == 0:
            header_sep = f"| {' | '.join(['---'] * len(cells))} |"
            rows.append(header_sep)
    return "\n".join(rows)


def parse_docx(path: Path) -> Dict[str, Any]:
    """Extract structured headings, paragraphs, and tables from DOCX."""
    import docx

    doc = docx.Document(str(path))
    parts: List[str] = []
    table_count = 0

    for element in doc.element.body:
        tag = element.tag.lower()
        if tag.endswith("p"):
            p = docx.text.paragraph.Paragraph(element, doc)
            text = p.text.strip()
            if text:
                style_name = p.style.name if p.style else ""
                if "Heading 1" in style_name:
                    parts.append(f"# {text}")
                elif "Heading 2" in style_name:
                    parts.append(f"## {text}")
                elif "Heading 3" in style_name:
                    parts.append(f"### {text}")
                else:
                    parts.append(text)
        elif tag.endswith("tbl"):
            table = docx.table.Table(element, doc)
            table_count += 1
            md_tbl = _docx_table_to_markdown(table)
            if md_tbl:
                parts.append(md_tbl)

    full_text = "\n\n".join(parts)
    return {
        "success": True,
        "filename": path.name,
        "file_type": "docx",
        "text": full_text,
        "page_count": max(1, len(doc.paragraphs) // 10),
        "tables_count": table_count,
        "is_scanned": False,
        "metadata": {
            "paragraphs": len(doc.paragraphs),
            "tables": table_count,
        },
    }


def parse_pptx(path: Path) -> Dict[str, Any]:
    """Extract slides, titles, shapes, tables, and speaker notes from PPTX."""
    from pptx import Presentation

    prs = Presentation(str(path))
    slides_text: List[str] = []

    for idx, slide in enumerate(prs.slides, start=1):
        slide_parts = [f"### Slide {idx}"]

        # Slide title
        if slide.shapes.title and slide.shapes.title.text.strip():
            slide_parts.append(f"**Title**: {slide.shapes.title.text.strip()}")

        for shape in slide.shapes:
            if shape == slide.shapes.title:
                continue

            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    t = p.text.strip()
                    if t:
                        slide_parts.append(f"- {t}")

            elif shape.has_table:
                tbl_rows = []
                for r_idx, row in enumerate(shape.table.rows):
                    cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    tbl_rows.append(f"| {' | '.join(cells)} |")
                    if r_idx == 0:
                        tbl_rows.append(f"| {' | '.join(['---'] * len(cells))} |")
                if tbl_rows:
                    slide_parts.append("\n".join(tbl_rows))

        # Speaker notes
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                slide_parts.append(f"*Speaker Notes*: {notes}")

        slides_text.append("\n".join(slide_parts))

    full_text = "\n\n---\n\n".join(slides_text)
    return {
        "success": True,
        "filename": path.name,
        "file_type": "pptx",
        "text": full_text,
        "page_count": len(prs.slides),
        "is_scanned": False,
        "metadata": {
            "slides_count": len(prs.slides),
        },
    }


def parse_xlsx(path: Path) -> Dict[str, Any]:
    """Extract sheets and format tabular data into Markdown tables."""
    import openpyxl

    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    sheets_text: List[str] = []

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        sheet_lines = [f"### Sheet: {sheet_name}"]

        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            continue

        formatted_rows = []
        for r_idx, row in enumerate(rows[:100]):
            cells = [str(c).strip() if c is not None else "" for c in row]
            if not any(cells):
                continue
            formatted_rows.append(f"| {' | '.join(cells)} |")
            if r_idx == 0:
                formatted_rows.append(f"| {' | '.join(['---'] * len(cells))} |")

        if len(rows) > 100:
            formatted_rows.append(f"*... ({len(rows) - 100} more rows truncated for context)*")

        sheet_lines.append("\n".join(formatted_rows))
        sheets_text.append("\n".join(sheet_lines))

    wb.close()
    full_text = "\n\n---\n\n".join(sheets_text)
    return {
        "success": True,
        "filename": path.name,
        "file_type": "xlsx",
        "text": full_text,
        "page_count": len(wb.sheetnames),
        "is_scanned": False,
        "metadata": {
            "sheet_names": wb.sheetnames,
        },
    }


def parse_csv(path: Path) -> Dict[str, Any]:
    """Parse CSV into formatted Markdown table."""
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    content = ""
    for enc in encodings:
        try:
            content = path.read_text(encoding=enc)
            break
        except Exception:
            continue

    lines = content.splitlines()
    reader = csv.reader(lines)
    formatted_rows = []
    for r_idx, row in enumerate(reader):
        if r_idx >= 100:
            formatted_rows.append(f"*... ({len(lines) - 100} more rows truncated)*")
            break
        cells = [c.strip() for c in row]
        if not any(cells):
            continue
        formatted_rows.append(f"| {' | '.join(cells)} |")
        if r_idx == 0:
            formatted_rows.append(f"| {' | '.join(['---'] * len(cells))} |")

    return {
        "success": True,
        "filename": path.name,
        "file_type": "csv",
        "text": "\n".join(formatted_rows) if formatted_rows else content,
        "page_count": max(1, len(lines) // 50),
        "is_scanned": False,
        "metadata": {"row_count": len(lines)},
    }


def parse_text(path: Path) -> Dict[str, Any]:
    """Multi-encoding reader for plain text, markdown, code, and logs."""
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    content = ""
    for enc in encodings:
        try:
            content = path.read_text(encoding=enc)
            break
        except Exception:
            continue

    lines = content.splitlines()
    return {
        "success": True,
        "filename": path.name,
        "file_type": path.suffix.lower().lstrip("."),
        "text": content,
        "page_count": max(1, len(lines) // 50),
        "is_scanned": False,
        "metadata": {"lines_count": len(lines)},
    }


def parse_dxf_document(path: Path) -> Dict[str, Any]:
    """Parse AutoCAD DXF drawing extracting layers, text, dimensions, and blocks."""
    try:
        import ezdxf
        doc = ezdxf.readfile(str(path))
        msp = doc.modelspace()

        layers = [layer.dxf.name for layer in doc.layers]
        texts = []
        for e in msp.query("TEXT MTEXT"):
            t = getattr(e.dxf, "text", "")
            if t:
                texts.append(t.strip())

        entities_count = len(list(msp))
        blocks = [b.name for b in doc.blocks if not b.name.startswith("*")]

        md_lines = [
            f"# CAD Engineering Drawing: {path.name}",
            f"- **Format**: AutoCAD DXF (AutoCAD Version: {doc.dxfversion})",
            f"- **Active Layers ({len(layers)})**: {', '.join(layers[:20])}",
            f"- **Total Vector Entities**: {entities_count}",
            f"- **Blocks/Symbols Defined**: {', '.join(blocks[:15]) if blocks else 'None'}",
            "",
            "## Extracted Drawing Text & Annotations:",
            "\n".join([f"- {txt}" for txt in texts[:50]]) if texts else "*(No direct text entities in model space)*",
        ]
        full_text = "\n".join(md_lines)

        return {
            "success": True,
            "filename": path.name,
            "file_type": "dxf",
            "text": full_text,
            "page_count": 1,
            "is_scanned": False,
            "metadata": {
                "layers": len(layers),
                "entities": entities_count,
                "text_elements": len(texts),
            },
        }
    except Exception as ex:
        logger.warning("dxf_parse_fallback", path=str(path), error=str(ex))
        return parse_text(path)


def parse_dwg_document(path: Path) -> Dict[str, Any]:
    """Extract readable engineering strings and metadata from binary DWG."""
    import re
    data = path.read_bytes()

    # Extract printable ASCII strings (minimum 4 chars)
    pattern = re.compile(rb"[\x20-\x7e]{4,}")
    raw_strings = [m.group(0).decode("ascii", errors="ignore").strip() for m in pattern.finditer(data)]

    meaningful = [
        s for s in raw_strings 
        if any(c.isalpha() for c in s) and not s.startswith("AcDb") and len(s) < 100
    ]
    unique_tokens = list(dict.fromkeys(meaningful))[:60]

    md_lines = [
        f"# AutoCAD Binary Drawing: {path.name}",
        "- **Format**: Autodesk DWG (Proprietary Binary CAD Container)",
        f"- **File Size**: {len(data) / 1024:.1f} KB",
        "",
        "## Recovered CAD Text, Layers & Metadata Tokens:",
        "\n".join([f"- {tok}" for tok in unique_tokens]) if unique_tokens else "*(Binary compressed container - no plain strings)*",
        "",
        "> [!NOTE]",
        "> DWG is a proprietary Autodesk binary container. For complete 1:1 vector entity inspection, save as `.dxf` or export as `.pdf` from AutoCAD or FreeCAD.",
    ]

    return {
        "success": True,
        "filename": path.name,
        "file_type": "dwg",
        "text": "\n".join(md_lines),
        "page_count": 1,
        "is_scanned": False,
        "metadata": {"binary_tokens_found": len(unique_tokens)},
    }


def parse_fcstd_document(path: Path) -> Dict[str, Any]:
    """Extract 3D model hierarchy, parts, and properties from FreeCAD .FCStd project."""
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        with zipfile.ZipFile(str(path), "r") as z:
            if "Document.xml" in z.namelist():
                xml_data = z.read("Document.xml")
                root = ET.fromstring(xml_data)

                objects = []
                for obj in root.findall(".//Object"):
                    name = obj.attrib.get("name", "")
                    obj_type = obj.attrib.get("type", "")
                    label_el = obj.find(".//Property[@name='Label']/String")
                    label = label_el.attrib.get("value", name) if label_el is not None else name
                    objects.append(f"{label} ({obj_type.split('::')[-1]})")

                md_lines = [
                    f"# FreeCAD Parametric Model: {path.name}",
                    "- **Format**: Native FreeCAD Project (.FCStd)",
                    f"- **Total Model Features**: {len(objects)}",
                    "",
                    "## Parametric Feature Tree:",
                    "\n".join([f"- {obj}" for obj in objects]) if objects else "*(Empty model tree)*",
                ]
                return {
                    "success": True,
                    "filename": path.name,
                    "file_type": "fcstd",
                    "text": "\n".join(md_lines),
                    "page_count": 1,
                    "is_scanned": False,
                    "metadata": {"objects_count": len(objects)},
                }
    except Exception as ex:
        logger.warning("fcstd_parse_failed", path=str(path), error=str(ex))

    return {
        "success": True,
        "filename": path.name,
        "file_type": "fcstd",
        "text": f"# FreeCAD Document: {path.name}\nNative binary CAD project archive.",
        "page_count": 1,
        "is_scanned": False,
    }


def parse_any_document(file_path: str | Path) -> Dict[str, Any]:
    """
    Unified entry point for reading any industrial document format:
    - Word: .docx, .doc
    - PowerPoint: .pptx, .ppt
    - Excel: .xlsx, .xls, .csv
    - PDF: .pdf
    - Text: .txt, .md, .log, .json, .yaml, .rst
    """
    path = Path(file_path)
    if not path.exists():
        logger.error("document_not_found", path=str(path))
        return {
            "success": False,
            "filename": path.name,
            "file_type": "unknown",
            "text": "",
            "page_count": 0,
            "error": "File not found",
        }

    ext = path.suffix.lower()

    try:
        if ext == ".pdf":
            parsed = parse_pdf(path)
            return {
                "success": True,
                "filename": path.name,
                "file_type": "pdf",
                "text": parsed.get("text", ""),
                "page_count": parsed.get("page_count", 1),
                "is_scanned": parsed.get("is_scanned", False),
                "metadata": parsed.get("metadata", {}),
            }

        elif ext in (".docx", ".doc"):
            return parse_docx(path)

        elif ext in (".pptx", ".ppt"):
            return parse_pptx(path)

        elif ext in (".xlsx", ".xls"):
            return parse_xlsx(path)

        elif ext == ".csv":
            return parse_csv(path)

        elif ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"):
            return {
                "success": True,
                "filename": path.name,
                "file_type": ext.lstrip("."),
                "text": f"Engineering drawing / visual inspection sheet: {path.name}",
                "page_count": 1,
                "is_scanned": True,
                "metadata": {"image_path": str(path)},
            }

        elif ext == ".dxf":
            return parse_dxf_document(path)

        elif ext == ".dwg":
            return parse_dwg_document(path)

        elif ext == ".fcstd":
            return parse_fcstd_document(path)

        else:
            # Plain text, Markdown, JSON, YAML, code
            return parse_text(path)

    except Exception as ex:
        logger.error("unified_document_parse_failed", path=str(path), error=str(ex))
        # Resilient fallback: read as raw text with error replacement
        raw_text = path.read_text(encoding="utf-8", errors="ignore")
        return {
            "success": False,
            "filename": path.name,
            "file_type": ext.lstrip("."),
            "text": raw_text[:5000],
            "page_count": 1,
            "is_scanned": False,
            "error": str(ex),
        }
