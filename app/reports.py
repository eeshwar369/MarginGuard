import io
from html import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def memo_pdf(memo: dict, workspace: str) -> bytes:
    output = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="MarginGuard decision memo",
        author=workspace,
    )
    content = memo["content"]
    body = [
        Paragraph("MarginGuard / Decision memo", styles["Title"]),
        Paragraph(escape(workspace), styles["Heading2"]),
        Paragraph(f"Status: <b>{escape(memo['status'].upper())}</b>", styles["Normal"]),
        Paragraph(f"Created: {escape(memo['created_at'])}", styles["Normal"]),
        Spacer(1, 7 * mm),
    ]
    if memo["status"] == "stale":
        body.append(
            Paragraph(
                "STALE: Data or assumptions changed. This memo is historical and requires a new review.",
                styles["Heading2"],
            )
        )
    if content.get("synthetic"):
        body.append(
            Paragraph("SYNTHETIC DEMONSTRATION DATA. This is not a real merchant result.", styles["Normal"])
        )
    body.append(Paragraph("Decision comparison", styles["Heading2"]))
    rows = [["Action", "Worst case (INR)", "Best case (INR)"]]
    for item in content["scenario"]["alternatives"]:
        rows.append([item["label"], f"{item['worst'] / 100:,.2f}", f"{item['best'] / 100:,.2f}"])
    table = Table(rows, colWidths=[80 * mm, 45 * mm, 45 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173d36")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
            ]
        )
    )
    body.append(table)
    body.append(Paragraph("Explicit assumptions", styles["Heading2"]))
    for text in content["scenario"]["assumptions"]:
        body.append(Paragraph(escape(text), styles["Normal"]))
        body.append(Spacer(1, 2 * mm))
    for key, value in content["scenario"]["params"].items():
        body.append(Paragraph(f"{escape(key.replace('_', ' '))}: {escape(str(value))}", styles["Normal"]))
    body.append(Paragraph("Evidence and provenance", styles["Heading2"]))
    body.append(
        Paragraph(
            f"Data version: {content['version']} / dataset {escape(memo['dataset_id'])}", styles["Normal"]
        )
    )
    body.append(Paragraph("Data SHA-256: " + escape(content["data_hash"]), styles["Normal"]))
    body.append(Paragraph("Scenario SHA-256: " + escape(memo["scenario_hash"]), styles["Normal"]))
    for item in content["findings"]:
        body.append(Paragraph(escape(f"{item['id']} — {item['title']} ({item['status']})"), styles["Normal"]))
    body.append(Spacer(1, 5 * mm))
    body.append(
        Paragraph(
            "Approval records a decision for this exact data and assumption version. No store settings, prices or external accounts are changed by this application.",
            styles["Normal"],
        )
    )
    doc.build(body)
    return output.getvalue()
