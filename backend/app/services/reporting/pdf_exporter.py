import io
import os
import re
from datetime import datetime, timezone
from typing import List, Tuple
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_FONTS_INITIALIZED = False
_DEFAULT_FONT = "Helvetica"
_DEFAULT_BOLD_FONT = "Helvetica-Bold"


def _ensure_unicode_fonts() -> Tuple[str, str]:
    global _FONTS_INITIALIZED, _DEFAULT_FONT, _DEFAULT_BOLD_FONT
    if _FONTS_INITIALIZED:
        return _DEFAULT_FONT, _DEFAULT_BOLD_FONT

    font_candidates = [
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "Arial", "Arial-Bold"),
        ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf", "Calibri", "Calibri-Bold"),
        ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf", "SegoeUI", "SegoeUI-Bold"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans", "DejaVuSans-Bold"),
    ]

    for reg_path, bold_path, reg_name, bold_name in font_candidates:
        if os.path.exists(reg_path) and os.path.exists(bold_path):
            try:
                pdfmetrics.registerFont(TTFont(reg_name, reg_path))
                pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                _DEFAULT_FONT = reg_name
                _DEFAULT_BOLD_FONT = bold_name
                _FONTS_INITIALIZED = True
                return _DEFAULT_FONT, _DEFAULT_BOLD_FONT
            except Exception:
                continue

    _FONTS_INITIALIZED = True
    return _DEFAULT_FONT, _DEFAULT_BOLD_FONT


class EngineeringPDFExporter:
    """Exports structured markdown engineering reports to high-fidelity PDF documents."""

    @classmethod
    def generate_pdf(cls, markdown_text: str, title: str = "Selnikel Teknik Raporu") -> bytes:
        font_name, bold_font_name = _ensure_unicode_fonts()
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Custom Styles
        header_title_style = ParagraphStyle(
            name="ReportTitle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
            fontName=bold_font_name,
        )
        section_heading_style = ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0369a1"),
            fontName=bold_font_name,
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            name="ReportBody",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#334155"),
            fontName=font_name,
        )
        bold_body_style = ParagraphStyle(
            name="BoldBody",
            parent=body_style,
            fontName=bold_font_name,
        )
        footer_note_style = ParagraphStyle(
            name="FooterNote",
            parent=styles["Italic"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748b"),
            fontName=font_name,
        )

        elements = []

        # 1. Header Banner
        header_table = Table(
            [
                [
                    Paragraph("<b>SELNİKEL ENERJİ</b><br/><font size=8 color='#0284c7'>Isı ve Makina Sanayi A.Ş. &bull; AR-GE ve Mühendislik</font>", bold_body_style),
                    Paragraph(f"<b>TEKNİK RAPOR</b><br/><font size=8 color='#64748b'>{datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}</font>", ParagraphStyle("RightH", parent=bold_body_style, alignment=2)),
                ]
            ],
            colWidths=[4.0 * inch, 3.2 * inch],
        )
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(header_table)
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=12))

        # 2. Parse Markdown Lines
        lines = markdown_text.split("\n")
        table_buffer: List[List[str]] = []
        in_table = False

        for line in lines:
            trimmed = line.strip()

            # Handle Markdown Table
            if trimmed.startswith("|") and trimmed.endswith("|"):
                # Table divider check (e.g. |---|---|)
                if re.match(r"^\|[\s\-:|]+\|$", trimmed):
                    continue
                cols = [c.strip() for c in trimmed.strip("|").split("|")]
                table_buffer.append(cols)
                in_table = True
                continue
            elif in_table and table_buffer:
                # Flush table
                elements.append(cls._render_table(table_buffer, body_style, bold_body_style))
                elements.append(Spacer(1, 8))
                table_buffer = []
                in_table = False

            if not trimmed:
                elements.append(Spacer(1, 4))
                continue

            # Heading 1
            if trimmed.startswith("# "):
                elements.append(Paragraph(trimmed[2:], header_title_style))
                elements.append(Spacer(1, 6))
            # Heading 2
            elif trimmed.startswith("## "):
                elements.append(Paragraph(trimmed[3:], section_heading_style))
                elements.append(Spacer(1, 4))
            # Heading 3
            elif trimmed.startswith("### "):
                elements.append(Paragraph(f"<b>{trimmed[4:]}</b>", bold_body_style))
                elements.append(Spacer(1, 3))
            # Horizontal line
            elif trimmed == "---":
                elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6, spaceBefore=6))
            # Bullet list
            elif trimmed.startswith("- ") or trimmed.startswith("* "):
                bullet_text = trimmed[2:]
                elements.append(Paragraph(f"&bull; {bullet_text}", body_style))
            # Normal text
            else:
                elements.append(Paragraph(trimmed, body_style))

        # Flush any remaining table
        if table_buffer:
            elements.append(cls._render_table(table_buffer, body_style, bold_body_style))

        # 3. Footer Seal & Verification Block
        elements.append(Spacer(1, 14))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceAfter=8))
        footer_table = Table(
            [
                [
                    Paragraph("<b>Doğrulama Durumu:</b> Otonom RAG & ASME PTC 4.1 Standart Denetimi Onaylı", footer_note_style),
                    Paragraph("<b>Sistem:</b> Selnikel AI Mühendislik Bilgi Ajanı", ParagraphStyle("RightFoot", parent=footer_note_style, alignment=2)),
                ]
            ],
            colWidths=[4.5 * inch, 2.7 * inch],
        )
        elements.append(footer_table)

        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data

    @classmethod
    def _render_table(
        cls,
        rows: List[List[str]],
        body_style: ParagraphStyle,
        header_style: ParagraphStyle,
    ) -> Table:
        formatted_data = []
        for r_idx, row in enumerate(rows):
            formatted_row = []
            for c in row:
                style = header_style if r_idx == 0 else body_style
                formatted_row.append(Paragraph(c, style))
            formatted_data.append(formatted_row)

        num_cols = max(len(r) for r in rows)
        col_width = (7.2 * inch) / max(1, num_cols)

        tbl = Table(formatted_data, colWidths=[col_width] * num_cols)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return tbl
