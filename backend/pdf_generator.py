"""Professional induction PDF generator using ReportLab.

The PDF is laid out as an A4 document with a coloured header band, sectioned
content (Personal, Business, Insurance, Medical History, HAVS, Declaration),
and a footer carrying the submission timestamp and employee reference.
"""
from __future__ import annotations

import base64
import io
from datetime import datetime, timezone
from typing import Any, Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepInFrame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

BRAND = colors.HexColor("#166534")
INK = colors.HexColor("#1C1917")
MUTED = colors.HexColor("#57534E")
LINE = colors.HexColor("#E7E5E4")
SOFT = colors.HexColor("#FAFAF9")

MEDICAL_QUESTIONS = [
    ("receiving_treatment", "Currently receiving treatment from a doctor/hospital"),
    ("prescribed_medication", "Taking prescribed medication"),
    ("medical_warning_card", "Carries a medical warning card"),
    ("pregnant", "Pregnant"),
    ("allergies", "Has any allergies"),
    ("asthma_bronchitis_chest", "Asthma, bronchitis or any chest condition"),
    ("fainting_blackouts_epilepsy", "Fainting, blackouts or epilepsy"),
    ("heart_problems", "Heart problems"),
    ("diabetes", "Diabetes"),
    ("bone_or_joint_disease", "Bone or joint disease"),
    ("skin_disease", "Skin disease"),
    ("persistent_bleeding_bruising", "Persistent bleeding or bruising"),
    ("liver_or_kidney_disease", "Liver or kidney disease"),
    ("havs_or_cts", "HAVS or Carpal Tunnel Syndrome (CTS)"),
    ("other_serious_illness", "Any other serious illness"),
]

HAVS_QUESTIONS = [
    ("tingling_after_vibration", "Tingling after vibration exposure"),
    ("tingling_other_times", "Tingling at other times"),
    ("night_pain_tingling_numbness", "Night pain, tingling or numbness"),
    ("finger_numbness_after_vibration", "Finger numbness after vibration"),
    ("fingers_white_in_cold", "Fingers go white in cold"),
    ("fingers_white_other_times", "Fingers go white at other times"),
    ("muscle_or_joint_problems", "Muscle or joint problems"),
    ("difficulty_handling_small_objects", "Difficulty handling small objects"),
]

DECLARATION = (
    "I confirm that the information provided in this induction is true, accurate and "
    "complete to the best of my knowledge. I understand that PNC will rely on this "
    "information for health, safety, insurance and compliance purposes, and that "
    "providing false or misleading information may result in immediate termination of "
    "engagement. By signing below I consent to PNC storing this information in line "
    "with applicable data protection laws and using it for the legitimate operation "
    "of my engagement as a subcontractor or employee."
)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["BodyText"]
    return {
        "h1": ParagraphStyle(
            "h1",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.white,
        ),
        "kicker": ParagraphStyle(
            "kicker",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#BBF7D0"),
            spaceAfter=2,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            textColor=BRAND,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "label": ParagraphStyle(
            "label",
            parent=base,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=MUTED,
        ),
        "value": ParagraphStyle(
            "value",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=INK,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base,
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=INK,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=MUTED,
            alignment=1,
        ),
    }


def _safe(v: Any) -> str:
    if v is None or v == "":
        return "—"
    return str(v)


def _kv_table(rows: Iterable[tuple[str, Any]], styles: dict[str, ParagraphStyle], col_widths=None) -> Table:
    data = []
    for label, value in rows:
        data.append(
            [
                Paragraph(label.upper(), styles["label"]),
                Paragraph(_safe(value), styles["value"]),
            ]
        )
    if col_widths is None:
        col_widths = [55 * mm, 110 * mm]
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, LINE),
            ]
        )
    )
    return t


def _yesno_table(items: Iterable[tuple[str, str, Any]], styles) -> Table:
    """items: (key, label, value) — value is 'yes' / 'no' / None."""
    data = [
        [
            Paragraph("QUESTION", styles["label"]),
            Paragraph("ANSWER", styles["label"]),
        ]
    ]
    for _, label, value in items:
        v = (value or "").lower()
        answer_text = "Yes" if v == "yes" else "No" if v == "no" else "—"
        text_color = colors.HexColor("#B91C1C") if v == "yes" else BRAND if v == "no" else MUTED
        data.append(
            [
                Paragraph(label, styles["body"]),
                Paragraph(
                    f'<para alignment="center"><font color="{text_color.hexval()}"><b>{answer_text}</b></font></para>',
                    styles["body"],
                ),
            ]
        )
        # we'll style per row below
    t = Table(data, colWidths=[125 * mm, 40 * mm], hAlign="LEFT", repeatRows=1)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, LINE),
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
    ]
    # Per-row tint on answer cell
    for idx, (_, _, value) in enumerate(items, start=1):
        v = (value or "").lower()
        if v == "yes":
            style.append(("BACKGROUND", (1, idx), (1, idx), colors.HexColor("#FEF2F2")))
        elif v == "no":
            style.append(("BACKGROUND", (1, idx), (1, idx), colors.HexColor("#F0FDF4")))
    t.setStyle(TableStyle(style))
    return t


def _on_first_page(canvas, doc, employee_id: str, full_name: str, submitted_at_iso: str):
    canvas.saveState()
    width, height = A4
    band_h = 32 * mm
    canvas.setFillColor(BRAND)
    canvas.rect(0, height - band_h, width, band_h, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#BBF7D0"))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(18 * mm, height - 13 * mm, "PNC INDUCTION RECORD")
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(18 * mm, height - 22 * mm, full_name or "Unnamed inductee")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(18 * mm, height - 28 * mm, f"Reference: {employee_id}")
    canvas.drawRightString(width - 18 * mm, height - 28 * mm, f"Submitted: {submitted_at_iso}")
    canvas.restoreState()
    _on_later_page(canvas, doc)


def _on_later_page(canvas, doc):
    canvas.saveState()
    width, _ = A4
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(18 * mm, 12 * mm, "PNC Induction Portal · confidential")
    canvas.drawRightString(width - 18 * mm, 12 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def _signature_image(data: dict) -> Image | None:
    """Try to embed the drawn signature.

    Preferred: data['signature_image_bytes'] (raw bytes from Storage).
    Fallback:  data['signature_image_data_url'] (base64 data URL).
    """
    raw: bytes | None = data.get("signature_image_bytes")
    if not raw:
        durl = data.get("signature_image_data_url")
        if durl and "," in durl:
            try:
                raw = base64.b64decode(durl.split(",", 1)[1])
            except Exception:
                raw = None
    if not raw:
        return None
    try:
        img = Image(io.BytesIO(raw))
        # scale to ~85mm wide, preserve aspect
        max_w = 85 * mm
        max_h = 35 * mm
        iw, ih = img.imageWidth, img.imageHeight
        scale = min(max_w / iw, max_h / ih)
        img.drawWidth = iw * scale
        img.drawHeight = ih * scale
        return img
    except Exception:
        return None


def build_induction_pdf(
    *,
    employee_id: str,
    employee: dict,
    medical: dict,
    havs: dict,
    documents_meta: dict,
    submitted_at: datetime | None = None,
) -> bytes:
    """Compose the induction PDF and return the raw PDF bytes.

    employee:  flat dict from the `employees` Firestore doc.
    medical:   dict from `medical_history`.
    havs:      dict from `havs_questionnaires`.
    documents_meta: e.g. {'files': {...}} from `employee_documents`.
    """
    styles = _styles()
    buf = io.BytesIO()

    submitted_at = submitted_at or datetime.now(timezone.utc)
    submitted_label = submitted_at.strftime("%d %b %Y · %H:%M UTC")

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=42 * mm,
        bottomMargin=20 * mm,
        title=f"PNC Induction — {employee.get('full_name','Inductee')}",
        author="PNC Induction Portal",
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        showBoundary=0,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )

    def first(canvas, d):
        _on_first_page(canvas, d, employee_id, employee.get("full_name", ""), submitted_label)

    doc.addPageTemplates(
        [
            PageTemplate(id="first", frames=frame, onPage=first),
            PageTemplate(id="later", frames=frame, onPage=_on_later_page),
        ]
    )

    story: list = []

    # ---- Personal ----
    story.append(Paragraph("Personal Information", styles["section"]))
    emergency = employee.get("emergency_contact") or {}
    story.append(
        _kv_table(
            [
                ("Full Name", employee.get("full_name")),
                ("Date of Birth", employee.get("dob")),
                ("Contact Telephone", employee.get("telephone")),
                ("Email Address", employee.get("email")),
                ("Address Line 1", employee.get("address1")),
                ("Postcode", employee.get("postcode")),
                ("National Insurance No.", employee.get("ni_number")),
                ("Emergency Contact", emergency.get("name")),
                ("Emergency Phone", emergency.get("phone")),
                ("Emergency Relationship", emergency.get("relationship")),
                ("Right To Work Share Code", employee.get("right_to_work_share_code")),
                ("DVLA Licence Check", employee.get("dvla_check", "").title() if employee.get("dvla_check") else ""),
            ],
            styles,
        )
    )

    # ---- Business ----
    story.append(Paragraph("Business Details", styles["section"]))
    biz = employee.get("business") or {}
    story.append(
        _kv_table(
            [
                ("Company Name", biz.get("company_name")),
                ("Bank Account Number", biz.get("bank_account")),
                ("Sort Code", biz.get("sort_code")),
                ("Company UTR", biz.get("utr")),
                ("VAT Registration", biz.get("vat_number")),
            ],
            styles,
        )
    )

    # ---- Insurance ----
    story.append(Paragraph("Insurance", styles["section"]))
    ins_label = (
        "Own insurance certificate"
        if employee.get("insurance_option") == "own"
        else "Covered by PNC (£5/week)"
        if employee.get("insurance_option") == "pnc"
        else None
    )
    story.append(_kv_table([("Insurance Choice", ins_label)], styles))

    # ---- Medical ----
    story.append(Paragraph("Medical History", styles["section"]))
    med_items = [(k, lbl, medical.get(k)) for k, lbl in MEDICAL_QUESTIONS]
    story.append(_yesno_table(med_items, styles))
    if medical.get("if_yes_details") or medical.get("medication_disability_details"):
        story.append(Spacer(1, 6))
        story.append(
            _kv_table(
                [
                    ("If Yes — Details", medical.get("if_yes_details")),
                    ("Medication / Disability", medical.get("medication_disability_details")),
                ],
                styles,
            )
        )

    # ---- HAVS ----
    story.append(Paragraph("HAVS Questionnaire", styles["section"]))
    havs_items = [(k, lbl, havs.get(k)) for k, lbl in HAVS_QUESTIONS]
    story.append(_yesno_table(havs_items, styles))

    # ---- Declaration & signature ----
    story.append(Paragraph("Declaration", styles["section"]))
    story.append(Paragraph(DECLARATION, styles["body"]))
    story.append(Spacer(1, 10))

    sig_img = _signature_image(documents_meta)
    sig_block = []
    if sig_img is not None:
        sig_block.append(sig_img)
    else:
        sig_block.append(Paragraph("<i>Drawn signature on file (image)</i>", styles["body"]))
    sig_block.append(Spacer(1, 4))
    sig_block.append(
        Paragraph(
            f"<b>Signed (typed):</b> {_safe(employee.get('digital_signature_name'))}<br/>"
            f"<b>Submitted:</b> {submitted_label}<br/>"
            f"<b>Reference:</b> {employee_id}",
            styles["body"],
        )
    )

    sig_table = Table(
        [[KeepInFrame(165 * mm, 60 * mm, sig_block)]],
        colWidths=[165 * mm],
    )
    sig_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(sig_table)

    # ---- Attached documents ----
    story.append(Paragraph("Uploaded Documents", styles["section"]))
    files = documents_meta.get("files") or {}
    def _doc_row(label: str, slot: str):
        f = files.get(slot) or {}
        return (label, f.get("name") or "Not provided")
    story.append(
        _kv_table(
            [
                _doc_row("Passport / ID", "passport"),
                _doc_row("Driving Licence", "driving_licence"),
                _doc_row("Insurance Certificate", "insurance_certificate"),
                _doc_row("Proof of Business Bank Account", "bank_proof"),
                _doc_row("Drawn Signature Image", "signature"),
            ],
            styles,
        )
    )

    doc.build(story)
    return buf.getvalue()
