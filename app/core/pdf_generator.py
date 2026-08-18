"""Rendert ein Anschreiben als formatiertes PDF (Geschaeftsbrief-Layout)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.core.profile import Profile


def generate_cover_letter_pdf(
    output_path: Path,
    profile: Profile,
    empfaenger_firma: str,
    empfaenger_ort: str,
    betreff: str,
    brieftext: str,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=11, leading=15, spaceAfter=10
    )
    sender_style = ParagraphStyle("Sender", parent=styles["Normal"], fontSize=10, leading=13)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=25 * mm,
        bottomMargin=20 * mm,
        leftMargin=25 * mm,
        rightMargin=20 * mm,
    )

    story = []

    absender_zeilen = [profile.name, profile.adresse, profile.telefon, profile.email]
    absender = "<br/>".join(z for z in absender_zeilen if z)
    if absender:
        story.append(Paragraph(absender, sender_style))
    story.append(Spacer(1, 14 * mm))

    empfaenger = "<br/>".join(z for z in [empfaenger_firma, empfaenger_ort] if z)
    if empfaenger:
        story.append(Paragraph(empfaenger, sender_style))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph(date.today().strftime("%d.%m.%Y"), sender_style))
    story.append(Spacer(1, 8 * mm))

    if betreff:
        story.append(Paragraph(f"<b>{betreff}</b>", body_style))
        story.append(Spacer(1, 4 * mm))

    for absatz in brieftext.split("\n\n"):
        absatz_html = absatz.strip().replace("\n", "<br/>")
        if absatz_html:
            story.append(Paragraph(absatz_html, body_style))

    doc.build(story)
    return output_path
