import io
import os
import logging
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128

log = logging.getLogger(__name__)

_FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "WorkSans")
_fonts_registered = False


def _register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return
    pdfmetrics.registerFont(TTFont("WorkSans-Regular", os.path.join(_FONTS_DIR, "WorkSans-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("WorkSans-Italic", os.path.join(_FONTS_DIR, "WorkSans-Italic.ttf")))
    pdfmetrics.registerFont(TTFont("WorkSans-Bold", os.path.join(_FONTS_DIR, "WorkSans-Bold.ttf")))
    _fonts_registered = True


def _safe(v):
    return "" if pd.isna(v) else str(v).strip()


def generate_labels_pdf(master_df, query_df, cruise_year="", box_number=""):
    """
    Returns (pdf_bytes: bytes, missing_field_numbers: list[str]).
    Raises ValueError if no matching records are found.
    """
    _register_fonts()

    q = query_df["Field Number"].astype(str).str.strip()
    m = master_df["Field Number"].astype(str).str.strip()

    missing = q[~q.isin(m)].tolist()

    records = master_df[m.isin(q)]
    if records.empty:
        raise ValueError("No matching field numbers found in the master spreadsheet.")

    FONT_SIZE = 7

    field_style = ParagraphStyle(
        name="Field", fontName="WorkSans-Bold", fontSize=FONT_SIZE + 4, leading=FONT_SIZE + 2, alignment=1
    )
    body_style = ParagraphStyle(
        name="Body", fontName="WorkSans-Regular", fontSize=FONT_SIZE, leading=FONT_SIZE, spaceBefore=0, spaceAfter=0
    )
    additional_label_style = ParagraphStyle(
        name="AdditionalLabel", fontName="WorkSans-Regular", fontSize=FONT_SIZE, leading=FONT_SIZE, alignment=1
    )

    label_w = 2.5 * inch
    cols = int(8.5 * inch // label_w)

    labels = []

    for _, r in records.iterrows():
        fn = _safe(r.get("Field Number"))
        count = _safe(r.get("Count"))
        n_text = f'<font name="WorkSans-Italic">n</font> = {count}' if count else '<font name="WorkSans-Italic">n</font> = __'

        barcode = code128.Code128(fn, barHeight=0.35 * inch, barWidth=0.01 * inch)

        clade = _safe(r.get("Clade/Family"))
        genus = _safe(r.get("Genus"))
        species = _safe(r.get("species"))
        gensp = " ".join(x for x in [genus, species] if x)

        taxon_parts = []
        if clade:
            taxon_parts.append(clade)
        if gensp:
            taxon_parts.append(f'<font name="WorkSans-Italic">{gensp}</font>')
        taxon_para = Paragraph(" ".join(taxon_parts), body_style)

        lat = _safe(r.get("End Lat"))
        lon = _safe(r.get("End Long"))
        coord = f"({lat}, {lon})" if lat and lon else ""

        maxd = _safe(r.get("Start (Max) Depth (m)"))
        mind = _safe(r.get("End (Min) Depth (m)"))
        depth = ""
        if maxd or mind:
            parts = []
            if maxd:
                parts.append(f"Max = {maxd}")
            if mind:
                parts.append(f"Min = {mind}")
            depth = "Depth (m): " + " | ".join(parts)

        date = _safe(r.get("Date Collected"))

        cruise_block = Paragraph(f"<u>Cruise</u><br/>{cruise_year}", additional_label_style)
        box_block = Paragraph(f"<u>Box</u><br/>{box_number}", additional_label_style)
        additional_table = Table(
            [[cruise_block], [box_block]],
            colWidths=[label_w * 0.3],
            rowHeights=[None, None],
        )
        additional_table.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))

        label = Table(
            [
                [Paragraph(fn, field_style), Paragraph(n_text, body_style)],
                [barcode, additional_table],
                [taxon_para, ""],
                [Paragraph(coord, body_style), ""],
                [Paragraph(depth, body_style), ""],
                [Paragraph(date, body_style), ""],
            ],
            colWidths=[label_w * 0.7, label_w * 0.3],
            rowHeights=[0.28 * inch, 0.42 * inch, None, None, None, None],
        )

        label.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, colors.black, 1, (1, 2)),
                ("SPAN", (0, 2), (1, 2)),
                ("SPAN", (0, 3), (1, 3)),
                ("SPAN", (0, 4), (1, 4)),
                ("SPAN", (0, 5), (1, 5)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("ALIGN", (1, 1), (1, 1), "CENTER"),
                ("VALIGN", (1, 1), (1, 1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 0.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
            ])
        )

        labels.append(label)

    grid, row = [], []
    for i, lbl in enumerate(labels):
        row.append(lbl)
        if (i + 1) % cols == 0:
            grid.append(row)
            row = []

    if row:
        while len(row) < cols:
            row.append("")
        grid.append(row)

    master_table = Table(grid, colWidths=[label_w] * cols)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=(8.5 * inch, 11 * inch))
    doc.build([master_table])

    return buf.getvalue(), missing
