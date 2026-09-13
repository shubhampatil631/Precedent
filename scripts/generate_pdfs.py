"""
scripts/generate_pdfs.py
Converts REPORT.md and DECISIONS.md into clean, publication-quality PDFs.
"""

import os
import re
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_header_footer(self, page_count):
        self.saveState()
        # Header
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(54, 750, "Precedent AI — Hiver SDE Intern Take-Home Submission (@AmericanAir)")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 744, 558, 744)

        # Footer
        self.line(54, 45, 558, 45)
        self.drawString(54, 32, "Confidential — Prepared for Hiver Evaluation (anurag@hiverhq.com)")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_text)
        self.restoreState()


def get_styles():
    styles = getSampleStyleSheet()
    
    primary_color = colors.HexColor("#1e3a8a")     # Deep Blue
    secondary_color = colors.HexColor("#2563eb")   # Brand Blue
    text_dark = colors.HexColor("#0f172a")         # Slate 900
    text_muted = colors.HexColor("#475569")        # Slate 600

    styles.add(ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=6
    ))

    styles.add(ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=text_muted,
        spaceAfter=14
    ))

    styles.add(ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=secondary_color,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        'H3',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=text_dark,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=text_dark,
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=text_dark,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    ))

    styles.add(ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=0
    ))

    styles.add(ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=text_dark
    ))

    styles.add(ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=primary_color
    ))

    styles.add(ParagraphStyle(
        'CodeBlock',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
        backColor=colors.HexColor("#f8fafc"),
        borderPadding=6,
        spaceAfter=6,
        spaceBefore=4
    ))

    styles.add(ParagraphStyle(
        'CalloutBox',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e40af"),
        backColor=colors.HexColor("#eff6ff"),
        borderColor=colors.HexColor("#bfdbfe"),
        borderWidth=0.5,
        borderPadding=6,
        spaceAfter=6
    ))

    return styles


def parse_markdown_to_elements(md_text: str, styles) -> list:
    elements = []
    lines = md_text.split("\n")
    in_code_block = False
    code_buffer = []
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            in_table = False
            return
        
        # Calculate max columns
        max_cols = max(len(r) for r in table_rows)
        # Pad shorter rows
        for r in table_rows:
            while len(r) < max_cols:
                r.append("")

        # Wrap in paragraphs
        formatted_table = []
        is_first_row = True
        for row in table_rows:
            formatted_row = []
            for cell in row:
                cell_clean = re.sub(r'[*_`]', '', cell).strip()
                if is_first_row:
                    p = Paragraph(f"<b>{cell_clean}</b>", styles['TableHeader'])
                else:
                    if cell.startswith("**") and cell.endswith("**"):
                        p = Paragraph(f"<b>{cell_clean}</b>", styles['TableCellBold'])
                    else:
                        p = Paragraph(cell_clean, styles['TableCell'])
                formatted_row.append(p)
            formatted_table.append(formatted_row)
            is_first_row = False

        col_width = 504.0 / max_cols
        t = Table(formatted_table, colWidths=[col_width] * max_cols)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        elements.append(Spacer(1, 3))
        elements.append(t)
        elements.append(Spacer(1, 6))
        table_rows = []
        in_table = False

    for line in lines:
        stripped = line.strip()

        # Code block toggle
        if stripped.startswith("```"):
            if in_code_block:
                in_code_block = False
                code_text = "\n".join(code_buffer)
                elements.append(Paragraph(f"<font name='Courier'>{code_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</font>", styles['CodeBlock']))
                code_buffer = []
            else:
                if in_table:
                    flush_table()
                in_code_block = True
                code_buffer = []
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        # Tables
        if "|" in stripped and stripped.startswith("|"):
            if re.match(r'^\|[\s:-|]+\|$', stripped):
                # Separator line like | :--- | :---: |
                continue
            if not in_table:
                in_table = True
                table_rows = []
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            table_rows.append(cells)
            continue
        elif in_table:
            flush_table()

        if not stripped:
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            elements.append(Spacer(1, 2))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6, spaceBefore=4))
            continue

        # Headings
        if stripped.startswith("# "):
            title_text = stripped[2:].strip()
            elements.append(Paragraph(title_text, styles['DocTitle']))
            continue
        if stripped.startswith("## "):
            h1_text = stripped[3:].strip()
            elements.append(Paragraph(h1_text, styles['H1']))
            continue
        if stripped.startswith("### "):
            h2_text = stripped[4:].strip()
            elements.append(Paragraph(h2_text, styles['H2']))
            continue
        if stripped.startswith("#### "):
            h3_text = stripped[5:].strip()
            elements.append(Paragraph(h3_text, styles['H3']))
            continue

        # Bullet list
        if stripped.startswith("- ") or stripped.startswith("* "):
            item_text = stripped[2:].strip()
            formatted_item = format_inline_markdown(item_text)
            elements.append(Paragraph(f"• {formatted_item}", styles['BulletText']))
            continue

        # Numbered list
        m = re.match(r'^(\d+)\.\s+(.*)$', stripped)
        if m:
            num = m.group(1)
            item_text = m.group(2)
            formatted_item = format_inline_markdown(item_text)
            elements.append(Paragraph(f"{num}. {formatted_item}", styles['BulletText']))
            continue

        # Regular Paragraph
        formatted_line = format_inline_markdown(stripped)
        elements.append(Paragraph(formatted_line, styles['CustomBody']))

    if in_table:
        flush_table()

    return elements


def format_inline_markdown(text: str) -> str:
    # Escape HTML entities first (except tags we generate)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Bold italic
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<b><i>\1</i></b>', text)
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Italic
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)
    # Code
    text = re.sub(r'`(.*?)`', r'<font name="Courier" color="#1e293b">\1</font>', text)
    # Links
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<font color="#2563eb"><u>\1</u></font>', text)

    return text


def build_pdf(md_filename: str, output_pdf_path: str, title: str):
    md_path = BASE_DIR / md_filename
    if not md_path.exists():
        print(f"Error: {md_path} not found")
        return

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = get_styles()
    story = parse_markdown_to_elements(md_text, styles)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] Created PDF: {output_pdf_path} (Size: {os.path.getsize(output_pdf_path)} bytes)")


def build_combined_submission_pdf():
    output_pdf_path = BASE_DIR / "Hiver_SDE_Intern_TakeHome_Report.pdf"
    
    report_text = ""
    with open(BASE_DIR / "REPORT.md", "r", encoding="utf-8") as f:
        report_text = f.read()

    decisions_text = ""
    with open(BASE_DIR / "DECISIONS.md", "r", encoding="utf-8") as f:
        decisions_text = f.read()

    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = get_styles()
    story = parse_markdown_to_elements(report_text, styles)
    story.append(PageBreak())
    story.extend(parse_markdown_to_elements(decisions_text, styles))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] Created Combined PDF: {output_pdf_path} (Size: {os.path.getsize(output_pdf_path)} bytes)")


if __name__ == "__main__":
    print("==================== GENERATING SUBMISSION PDFS ====================")
    build_pdf("REPORT.md", BASE_DIR / "REPORT.pdf", "Evaluation Report")
    build_pdf("DECISIONS.md", BASE_DIR / "DECISIONS.pdf", "Decision Log")
    build_combined_submission_pdf()
    print("==================== PDF GENERATION COMPLETE ====================")
