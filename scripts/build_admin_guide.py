"""Render ADMIN_USER_GUIDE.md → ADMIN_USER_GUIDE.pdf using ReportLab.

Lightweight Markdown handling: H1/H2/H3, paragraphs, bullet lists, code fences
and pipe tables (since that's everything used in the source guide). Branded
header band and footer match the induction PDF style for consistency.
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageBreak, PageTemplate,
    Paragraph, Preformatted, Spacer, Table, TableStyle,
)

BRAND = colors.HexColor("#166534")
INK = colors.HexColor("#1C1917")
MUTED = colors.HexColor("#57534E")
LINE = colors.HexColor("#E7E5E4")
SOFT = colors.HexColor("#FAFAF9")

base = getSampleStyleSheet()["BodyText"]
H1 = ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=INK, spaceAfter=10)
H2 = ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=BRAND, spaceBefore=14, spaceAfter=6)
H3 = ParagraphStyle("h3", parent=base, fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=INK, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("body", parent=base, fontName="Helvetica", fontSize=10, leading=14, textColor=INK, spaceAfter=4)
SMALL = ParagraphStyle("small", parent=base, fontName="Helvetica-Oblique", fontSize=8.5, leading=11, textColor=MUTED)
LISTITEM = ParagraphStyle("li", parent=BODY, leftIndent=12, bulletIndent=2, spaceAfter=2)
CODE = ParagraphStyle("code", parent=base, fontName="Courier", fontSize=8.5, leading=11, textColor=INK, leftIndent=8, rightIndent=8, backColor=SOFT)


def first_page(canvas, doc):
    w, h = A4
    canvas.saveState()
    band = 32 * mm
    canvas.setFillColor(BRAND)
    canvas.rect(0, h - band, w, band, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#BBF7D0"))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(18 * mm, h - 13 * mm, "PNC INDUCTION SYSTEM")
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString(18 * mm, h - 22 * mm, "Admin User Guide")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(18 * mm, h - 28 * mm, "Version 1.0 · February 2026")
    footer(canvas, doc)
    canvas.restoreState()


def footer(canvas, doc):
    w, _ = A4
    canvas.saveState()
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(18 * mm, 12 * mm, "PNC Induction System · Admin User Guide · confidential")
    canvas.drawRightString(w - 18 * mm, 12 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def later_page(canvas, doc):
    footer(canvas, doc)


def _escape(text: str) -> str:
    # ReportLab paragraph parser uses XML-ish syntax. Escape HTML-special chars
    # and turn **bold** / *italic* / `code` into <b>/<i>/<font color="">.
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier" color="#1C1917" backColor="#FAFAF9">\1</font>', text)
    return text


def _flush_para(buf: list[str], flow: list, style):
    if buf:
        flow.append(Paragraph(_escape(" ".join(buf).strip()), style))
        buf.clear()


def _flush_table(rows: list[list[str]], flow: list):
    if not rows:
        return
    data = [[Paragraph(_escape(c), BODY) for c in row] for row in rows]
    col_count = max(len(r) for r in rows)
    width = 165 * mm
    col_widths = [width / col_count] * col_count
    t = Table(data, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRAND),
        ("BOX", (0, 0), (-1, -1), 0.25, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    flow.append(t)
    flow.append(Spacer(1, 6))


def _flush_list(items: list[str], flow: list):
    for it in items:
        flow.append(Paragraph(f"• {_escape(it)}", LISTITEM))


def render(md_path: Path, pdf_path: Path) -> int:
    text = md_path.read_text(encoding="utf-8")

    doc = BaseDocTemplate(
        str(pdf_path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=42 * mm, bottomMargin=20 * mm,
        title="PNC Induction System — Admin User Guide",
        author="PNC",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([
        PageTemplate(id="first", frames=frame, onPage=first_page),
        PageTemplate(id="later", frames=frame, onPage=later_page),
    ])

    flow: list = []
    para_buf: list[str] = []
    list_buf: list[str] = []
    table_buf: list[list[str]] = []
    code_buf: list[str] = []
    in_code = False
    skipped_first_h1 = False

    def flush_all():
        _flush_para(para_buf, flow, BODY)
        if list_buf:
            _flush_list(list_buf, flow)
            list_buf.clear()
        if table_buf:
            _flush_table(table_buf, flow)
            table_buf.clear()

    for raw in text.splitlines():
        line = raw.rstrip()

        # Code fences ```
        if line.strip().startswith("```"):
            if in_code:
                flush_all()
                flow.append(Preformatted("\n".join(code_buf), CODE))
                flow.append(Spacer(1, 6))
                code_buf.clear()
                in_code = False
            else:
                flush_all()
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        # Tables (pipe-style). A row of "---" separates header from body — skip it.
        if "|" in line and line.strip().startswith("|") and line.strip().endswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-+:?", c) for c in cells):
                continue
            table_buf.append(cells)
            continue
        elif table_buf:
            _flush_table(table_buf, flow)
            table_buf.clear()

        # Headings
        if line.startswith("# "):
            flush_all()
            heading = line[2:].strip()
            if not skipped_first_h1:
                skipped_first_h1 = True  # don't repeat the cover title
                continue
            flow.append(PageBreak())
            flow.append(Paragraph(_escape(heading), H1))
            continue
        if line.startswith("## "):
            flush_all()
            flow.append(Paragraph(_escape(line[3:].strip()), H2))
            continue
        if line.startswith("### "):
            flush_all()
            flow.append(Paragraph(_escape(line[4:].strip()), H3))
            continue

        # Lists
        stripped = line.lstrip()
        if stripped.startswith(("- ", "* ")):
            _flush_para(para_buf, flow, BODY)
            list_buf.append(stripped[2:].strip())
            continue
        else:
            if list_buf:
                _flush_list(list_buf, flow)
                list_buf.clear()

        # Horizontal rule / blank / quote — flush paragraph
        if line.strip() == "" or line.strip().startswith("---"):
            _flush_para(para_buf, flow, BODY)
            if line.strip().startswith("---"):
                flow.append(Spacer(1, 4))
            continue
        if line.strip().startswith(">"):
            _flush_para(para_buf, flow, BODY)
            flow.append(Paragraph(_escape(line.strip().lstrip(">").strip()), SMALL))
            continue
        if line.strip().startswith("_") and line.strip().endswith("_") and line.count("_") >= 2:
            _flush_para(para_buf, flow, BODY)
            inner = line.strip().strip("_")
            flow.append(Paragraph(f"<i>{_escape(inner)}</i>", SMALL))
            continue

        para_buf.append(line.strip())

    flush_all()
    doc.build(flow)
    return pdf_path.stat().st_size


if __name__ == "__main__":
    size = render(Path("/app/ADMIN_USER_GUIDE.md"), Path("/app/ADMIN_USER_GUIDE.pdf"))
    print(f"Generated /app/ADMIN_USER_GUIDE.pdf ({size:,} bytes)")
