from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas import InvoiceLine, InvoiceRead

_GROUP_ORDER = ("pitch", "person", "service", "custom")
_GROUP_TITLES = {
    "pitch": "Zeltplätze",
    "person": "Personen",
    "service": "Zusatzdienste",
    "custom": "Sonstige Positionen",
}


def _money(value: float) -> str:
    return f"{value:.2f} €"


def _lines_by_category(lines: list[InvoiceLine]) -> list[tuple[str, list[InvoiceLine]]]:
    buckets: dict[str, list[InvoiceLine]] = {key: [] for key in _GROUP_ORDER}
    for line in lines:
        if line.category in buckets:
            buckets[line.category].append(line)
        else:
            buckets.setdefault(line.category, []).append(line)
    groups: list[tuple[str, list[InvoiceLine]]] = []
    for key in _GROUP_ORDER:
        if buckets[key]:
            groups.append((key, buckets[key]))
    for key, items in buckets.items():
        if key not in _GROUP_ORDER and items:
            groups.append((key, items))
    return groups


def _escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _period_short(start, end) -> str:
    """Day+month only — year is redundant in the period column."""
    return f"{start.strftime('%d.%m.')} – {end.strftime('%d.%m.')}"


def _address_html(address: str) -> str:
    return "<br/>".join(_escape(part) for part in (address or "").splitlines() if part.strip())


def render_invoice_pdf(invoice: InvoiceRead, logo_file: Path | None = None) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Title"],
        fontSize=16,
        spaceAfter=6,
        alignment=0,
    )
    small = ParagraphStyle("InvoiceSmall", parent=styles["Normal"], fontSize=9, leading=12)
    cell_style = ParagraphStyle(
        "InvoiceCell",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
    )
    cell_right = ParagraphStyle(
        "InvoiceCellRight",
        parent=cell_style,
        alignment=2,  # TA_RIGHT
    )
    footer_style = ParagraphStyle("InvoiceFooter", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#444444"))

    operator = invoice.operator
    story: list = []

    header_cells: list = []
    if logo_file and logo_file.is_file():
        try:
            from reportlab.lib.utils import ImageReader

            # Validate readable image, then pass path (Image() does not accept ImageReader)
            ImageReader(str(logo_file)).getSize()
            img = Image(str(logo_file))
            img._restrictSize(35 * mm, 25 * mm)
            header_cells.append(img)
        except Exception:
            header_cells.append("")
    else:
        header_cells.append("")

    org_bits = []
    if operator.organization_name:
        org_bits.append(f"<b>{_escape(operator.organization_name)}</b>")
    if operator.address:
        org_bits.append(_address_html(operator.address))
    header_cells.append(Paragraph("<br/>".join(org_bits) if org_bits else "", small))

    if any(header_cells):
        header = Table([header_cells], colWidths=[40 * mm, 130 * mm])
        header.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        story.append(header)
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2f5d3a")))
        story.append(Spacer(1, 8))

    story.extend(
        [
            Paragraph("Rechnung / Abrechnung", title_style),
            Spacer(1, 4),
            Paragraph(f"<b>Gruppe:</b> {_escape(invoice.group_name)}", styles["Normal"]),
            Paragraph(
                f"<b>Zeitraum:</b> {invoice.start_date.isoformat()} – {invoice.end_date.isoformat()} "
                f"({invoice.nights} Nächte)",
                styles["Normal"],
            ),
            Paragraph(
                f"<b>Rechnungsnummer:</b> {_escape(invoice.invoice_number or '—')}",
                styles["Normal"],
            ),
            Paragraph(f"<b>Buchung-Nr:</b> {invoice.booking_id}", styles["Normal"]),
            Spacer(1, 12),
        ]
    )

    def _cell(text: str, style: ParagraphStyle = cell_style) -> Paragraph:
        return Paragraph(_escape(text), style)

    data: list[list] = [
        [
            _cell("Position"),
            _cell("Menge", cell_right),
            _cell("Tagespreis", cell_right),
            _cell("Zeitraum", cell_right),
            _cell("Nächte", cell_right),
            _cell("Betrag", cell_right),
        ]
    ]
    special_rows: list[tuple[int, str]] = []

    for category, group_lines in _lines_by_category(invoice.lines):
        title = _GROUP_TITLES.get(category, category)
        data.append([_cell(title), "", "", "", "", ""])
        special_rows.append((len(data) - 1, "header"))
        subtotal = 0.0
        for line in group_lines:
            period = ""
            if line.start_date and line.end_date:
                period = _period_short(line.start_date, line.end_date)
            if category == "custom":
                data.append(
                    [
                        _cell(line.label),
                        _cell("—", cell_right),
                        _cell("—", cell_right),
                        "",
                        _cell("—", cell_right),
                        _cell(_money(line.amount), cell_right),
                    ]
                )
            else:
                data.append(
                    [
                        _cell(line.label),
                        _cell(f"{line.quantity:g}", cell_right),
                        _cell(_money(line.unit_price), cell_right),
                        _cell(period, cell_right),
                        _cell(str(line.nights), cell_right),
                        _cell(_money(line.amount), cell_right),
                    ]
                )
            subtotal += line.amount
        data.append(
            ["", "", "", "", _cell("Zwischensumme", cell_right), _cell(_money(subtotal), cell_right)]
        )
        special_rows.append((len(data) - 1, "subtotal"))

    data.append(
        ["", "", "", "", _cell("Summe", cell_right), _cell(_money(invoice.total), cell_right)]
    )
    special_rows.append((len(data) - 1, "total"))

    # Paragraph cells keep text inside colWidths; description (col 0) may wrap.
    table = Table(
        data,
        colWidths=[65 * mm, 16 * mm, 22 * mm, 28 * mm, 16 * mm, 22 * mm],
        repeatRows=1,
    )
    style_cmds: list = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f5d3a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, 0), 0.3, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for row_idx, kind in special_rows:
        if kind == "header":
            style_cmds.extend(
                [
                    ("SPAN", (0, row_idx), (-1, row_idx)),
                    ("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#e8efe9")),
                    ("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold"),
                    ("ALIGN", (0, row_idx), (0, row_idx), "LEFT"),
                    ("LINEBELOW", (0, row_idx), (-1, row_idx), 0.3, colors.grey),
                ]
            )
        elif kind == "subtotal":
            style_cmds.extend(
                [
                    ("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold"),
                    ("LINEABOVE", (0, row_idx), (-1, row_idx), 0.4, colors.grey),
                    ("LINEBELOW", (0, row_idx), (-1, row_idx), 0.3, colors.grey),
                ]
            )
        elif kind == "total":
            style_cmds.extend(
                [
                    ("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold"),
                    ("LINEABOVE", (0, row_idx), (-1, row_idx), 1.0, colors.HexColor("#2f5d3a")),
                ]
            )
    for r in range(1, len(data)):
        kinds = {k for i, k in special_rows if i == r}
        if "header" not in kinds:
            style_cmds.append(("BOX", (0, r), (-1, r), 0.2, colors.Color(0.85, 0.85, 0.85)))

    table.setStyle(TableStyle(style_cmds))
    story.append(table)

    sig_label = ParagraphStyle(
        "InvoiceSigLabel",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#444444"),
        spaceBefore=4,
    )
    signature_cell = Table(
        [
            [""],
            [Paragraph("Bestätigung Gruppenleiter", sig_label)],
        ],
        colWidths=[78 * mm],
        rowHeights=[22 * mm, None],
    )
    signature_cell.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (0, 0), 1, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    signature_cell_qm = Table(
        [
            [""],
            [Paragraph("Unterschrift Quartermaster", sig_label)],
        ],
        colWidths=[78 * mm],
        rowHeights=[22 * mm, None],
    )
    signature_cell_qm.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (0, 0), 1, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    signatures = Table(
        [[signature_cell, signature_cell_qm]],
        colWidths=[85 * mm, 85 * mm],
    )
    signatures.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 12),
            ]
        )
    )
    story.append(Spacer(1, 28))
    story.append(signatures)

    footer_parts = []
    if operator.organization_name:
        footer_parts.append(_escape(operator.organization_name))
    if operator.address:
        footer_parts.append(_address_html(operator.address).replace("<br/>", " · "))
    if operator.iban:
        footer_parts.append(f"IBAN: {_escape(operator.iban)}")
    if footer_parts:
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        story.append(Spacer(1, 6))
        story.append(Paragraph(" · ".join(footer_parts), footer_style))

    doc.build(story)
    return buffer.getvalue()
