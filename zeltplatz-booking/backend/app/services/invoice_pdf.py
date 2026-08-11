from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas import InvoiceLine, InvoiceRead

_GROUP_ORDER = ("pitch", "person", "service")
_GROUP_TITLES = {
    "pitch": "Zeltplätze",
    "person": "Personen",
    "service": "Zusatzdienste",
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
            # #region agent log
            try:
                import json, time
                from pathlib import Path as _P
                _log = _P(__file__).resolve().parents[4] / ".cursor" / "debug-188c80.log"
                _log.parent.mkdir(parents=True, exist_ok=True)
                with _log.open("a", encoding="utf-8") as _f:
                    _f.write(json.dumps({"sessionId":"188c80","runId":"post-fix","hypothesisId":"B","location":"invoice_pdf.py:logo","message":"logo embedded","data":{"path":str(logo_file),"drawW":float(img.drawWidth),"drawH":float(img.drawHeight)},"timestamp":int(time.time()*1000)})+"\n")
            except Exception:
                pass
            # #endregion
        except Exception as e:
            # #region agent log
            try:
                import json, time
                from pathlib import Path as _P
                _log = _P(__file__).resolve().parents[4] / ".cursor" / "debug-188c80.log"
                _log.parent.mkdir(parents=True, exist_ok=True)
                with _log.open("a", encoding="utf-8") as _f:
                    _f.write(json.dumps({"sessionId":"188c80","runId":"post-fix","hypothesisId":"B","location":"invoice_pdf.py:logo:error","message":"logo embed failed","data":{"path":str(logo_file),"errorType":type(e).__name__,"error":str(e)},"timestamp":int(time.time()*1000)})+"\n")
            except Exception:
                pass
            # #endregion
            header_cells.append("")
    else:
        # #region agent log
        try:
            import json, time
            from pathlib import Path as _P
            _log = _P(__file__).resolve().parents[4] / ".cursor" / "debug-188c80.log"
            _log.parent.mkdir(parents=True, exist_ok=True)
            with _log.open("a", encoding="utf-8") as _f:
                _f.write(json.dumps({"sessionId":"188c80","runId":"post-fix","hypothesisId":"A","location":"invoice_pdf.py:logo:missing","message":"no logo file for pdf","data":{"logo_file":str(logo_file) if logo_file else None,"is_file":bool(logo_file and logo_file.is_file())},"timestamp":int(time.time()*1000)})+"\n")
        except Exception:
            pass
        # #endregion
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
            Paragraph(f"<b>Buchung-Nr:</b> {invoice.booking_id}", styles["Normal"]),
            Spacer(1, 12),
        ]
    )

    data = [["Position", "Menge", "Tagespreis", "Zeitraum", "Nächte", "Betrag"]]
    special_rows: list[tuple[int, str]] = []

    for category, group_lines in _lines_by_category(invoice.lines):
        title = _GROUP_TITLES.get(category, category)
        data.append([title, "", "", "", "", ""])
        special_rows.append((len(data) - 1, "header"))
        subtotal = 0.0
        for line in group_lines:
            period = ""
            if line.start_date and line.end_date:
                period = f"{line.start_date.isoformat()} – {line.end_date.isoformat()}"
            data.append(
                [
                    line.label,
                    f"{line.quantity:g}",
                    _money(line.unit_price),
                    period,
                    str(line.nights),
                    _money(line.amount),
                ]
            )
            subtotal += line.amount
        data.append(["", "", "", "", "Zwischensumme", _money(subtotal)])
        special_rows.append((len(data) - 1, "subtotal"))

    data.append(["", "", "", "", "Summe", _money(invoice.total)])
    special_rows.append((len(data) - 1, "total"))

    table = Table(data, colWidths=[55 * mm, 16 * mm, 22 * mm, 38 * mm, 16 * mm, 22 * mm])
    style_cmds: list = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f5d3a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, 0), 0.3, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
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
