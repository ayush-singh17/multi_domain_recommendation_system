"""
PDF Report Generator
Journal Recommendation System

Fixes applied:
  1. Unified metadata block — all fields in consistent 2-column grid, no truncation
  2. Interdisciplinary Bridge tag — shown when BERT high + BM25 low
  3. Score breakdown always visible — removed KeepTogether wrapping that
     caused truncation when entries split across pages
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ── Colour palette ────────────────────────────────────────────────────────────
C_DARK   = colors.HexColor("#0b0f1a")
C_BLUE   = colors.HexColor("#5a8aff")
C_GREEN  = colors.HexColor("#4caf82")
C_AMBER  = colors.HexColor("#c49a3c")
C_RED    = colors.HexColor("#e07070")
C_MID    = colors.HexColor("#6a7490")
C_BORDER = colors.HexColor("#d0cdc8")
C_BG_A   = colors.HexColor("#eef2ff")
C_BG_B   = colors.HexColor("#eef7f2")
C_BG_C   = colors.HexColor("#fdf8ee")
C_TAG_ID = colors.HexColor("#7b5ea7")   # purple for interdisciplinary bridge tag


def build_styles():
    return {
        "title": ParagraphStyle(
            "title", fontName="Helvetica-Bold", fontSize=22,
            textColor=C_DARK, spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName="Helvetica", fontSize=10,
            textColor=C_MID, spaceAfter=2,
        ),
        "section": ParagraphStyle(
            "section", fontName="Helvetica-Bold", fontSize=11,
            textColor=C_BLUE, spaceBefore=14, spaceAfter=4,
        ),
        "journal_title": ParagraphStyle(
            "journal_title", fontName="Helvetica-Bold", fontSize=10,
            textColor=C_DARK, spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=8.5,
            textColor=C_DARK, leading=13, spaceAfter=3,
        ),
        "small": ParagraphStyle(
            "small", fontName="Helvetica", fontSize=7.5,
            textColor=C_MID, leading=11,
        ),
        "small_bold": ParagraphStyle(
            "small_bold", fontName="Helvetica-Bold", fontSize=7.5,
            textColor=C_MID, leading=11,
        ),
        "abstract": ParagraphStyle(
            "abstract", fontName="Helvetica-Oblique", fontSize=8.5,
            textColor=C_MID, leading=13, leftIndent=10, rightIndent=10,
        ),
        "signal_ok": ParagraphStyle(
            "signal_ok", fontName="Helvetica", fontSize=8,
            textColor=C_GREEN, leading=12,
        ),
        "signal_warn": ParagraphStyle(
            "signal_warn", fontName="Helvetica", fontSize=8,
            textColor=C_AMBER, leading=12,
        ),
        "signal_bad": ParagraphStyle(
            "signal_bad", fontName="Helvetica", fontSize=8,
            textColor=C_RED, leading=12,
        ),
        "bridge_tag": ParagraphStyle(
            "bridge_tag", fontName="Helvetica-Bold", fontSize=7.5,
            textColor=C_TAG_ID, leading=11,
        ),
        "score": ParagraphStyle(
            "score", fontName="Helvetica-Bold", fontSize=14,
            textColor=C_BLUE, alignment=TA_RIGHT,
        ),
        "disclaimer": ParagraphStyle(
            "disclaimer", fontName="Helvetica-Oblique", fontSize=7.5,
            textColor=C_MID, alignment=TA_CENTER, spaceBefore=12,
        ),
    }


def risk_color(risk_level):
    return {"Low": C_GREEN, "Medium": C_AMBER, "High": C_RED}.get(risk_level, C_MID)


def plan_label(plan_key):
    return {
        "A": "Plan A — Ambitious (Q1)",
        "B": "Plan B — Balanced (Q2)",
        "C": "Plan C — Safe Fallback (Q3/Q4)",
    }.get(plan_key, f"Plan {plan_key}")


def plan_desc(plan_key):
    return {
        "A": "Top-tier journals. High competition but maximum academic impact.",
        "B": "Strong journals with a higher acceptance rate than Q1.",
        "C": "Lower-tier but indexed journals. Faster acceptance.",
    }.get(plan_key, "")


def is_interdisciplinary_bridge(exp: dict) -> bool:
    """
    Returns True when BERT detected semantic relevance
    but keyword overlap was low — the 'contextual bridge' case.
    """
    return (
        exp.get("bert_score", 0) > 0.80 and
        exp.get("bm25_score", 0) < 3.0 and
        len(exp.get("matched_tokens", [])) <= 1
    )


def _weeks_display(exp: dict) -> str:
    """Format weeks/months to publication for PDF display."""
    weeks  = exp.get("weeks_to_publish")
    months = exp.get("months_to_publish")
    if weeks is None or str(weeks) == "nan":
        return "Not available"
    try:
        w = int(float(weeks))
        m = round(float(months), 1) if months else round(w / 4.33, 1)
        return f"~{w} weeks (~{m} months)"
    except:
        return "Not available"


def _apc_display(exp: dict) -> str:
    """Format APC for PDF display."""
    oa = str(exp.get("open_access", "")).strip()
    if oa != "Yes":
        return "Subscription"
    apc_amt = exp.get("apc_amount")
    apc_usd = exp.get("apc_usd")
    if apc_amt == 0:
        return "Free (Diamond OA)"
    if apc_usd and apc_usd > 0:
        curr = exp.get("apc_currency", "USD")
        return f"~${int(apc_usd):,} USD ({curr})"
    return "Open Access (APC unknown)"


def render_journal(exp: dict, option_num: int, styles: dict) -> list:
    """
    Renders one journal as a flat list of flowables.
    No KeepTogether wrapper — avoids score breakdown being cut off.

    Fix 1: Unified metadata block (consistent 2-column grid)
    Fix 2: Interdisciplinary Bridge tag
    Fix 3: Score breakdown always at end, never wrapped away
    """
    elements = []
    score_pct = int(exp["final_score"] * 100)
    oa_text   = "  Open Access" if str(exp["open_access"]).strip() == "Yes" else ""

    # ── FIX 1: Unified header row ─────────────────────────────────────────
    header_data = [[
        Paragraph(f"<b>#{option_num}  {exp['title']}</b>", styles["journal_title"]),
        Paragraph(f"<b>{score_pct}%</b>", styles["score"]),
    ]]
    header_tbl = Table(header_data, colWidths=[13*cm, 3.5*cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
    ]))
    elements.append(header_tbl)

    # Tags line
    tags = f"{exp['quartile']}  •  Risk: {exp['risk_level']}{oa_text}"
    elements.append(Paragraph(tags, styles["small"]))

    # ── FIX 2: Interdisciplinary Bridge tag ───────────────────────────────
    if is_interdisciplinary_bridge(exp):
        elements.append(Spacer(1, 3))
        elements.append(Paragraph(
            "◆  Interdisciplinary Bridge — high semantic similarity detected "
            "across disciplines despite limited keyword overlap",
            styles["bridge_tag"]
        ))

    elements.append(Spacer(1, 5))

    # ── FIX 1: Unified metadata block — 2-column grid ─────────────────────
    # Every field uses the same label-width (2.2cm) + value-width (5.3cm)
    # Two pairs per row, consistent across all journal entries
    meta_rows = [
        [
            Paragraph("<b>Publisher</b>", styles["small"]),
            Paragraph(str(exp["publisher"]), styles["small"]),
            Paragraph("<b>H-index</b>", styles["small"]),
            Paragraph(str(exp["h_index"]), styles["small"]),
        ],
        [
            Paragraph("<b>SJR</b>", styles["small"]),
            Paragraph(str(exp["sjr"]), styles["small"]),
            Paragraph("<b>ISSN</b>", styles["small"]),
            Paragraph(str(exp["issn"]), styles["small"]),
        ],
        [
            Paragraph("<b>Coverage</b>", styles["small"]),
            Paragraph(str(exp["coverage"]), styles["small"]),
            Paragraph("<b>APC</b>", styles["small"]),
            Paragraph(_apc_display(exp), styles["small"]),
        ],
        [
            Paragraph("<b>Avg. Time to Publish</b>", styles["small"]),
            Paragraph(_weeks_display(exp), styles["small"]),
            Paragraph("", styles["small"]),
            Paragraph("", styles["small"]),
        ],
        [
            Paragraph("<b>Areas</b>", styles["small"]),
            Paragraph(str(exp["areas"]), styles["small"]),
            Paragraph("", styles["small"]),
            Paragraph("", styles["small"]),
        ],
    ]

    meta_tbl = Table(
        meta_rows,
        colWidths=[2.2*cm, 5.3*cm, 2.2*cm, 6.8*cm]
    )
    meta_tbl.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        # Light horizontal rule between rows
        ("LINEBELOW",     (0, 0), (-1, -2), 0.3, C_BORDER),
    ]))
    elements.append(meta_tbl)
    elements.append(Spacer(1, 7))

    # ── Why recommended ───────────────────────────────────────────────────
    elements.append(Paragraph("<b>Why recommended</b>", styles["small_bold"]))
    if exp.get("matched_tokens"):
        tokens_str = ", ".join(exp["matched_tokens"][:6])
        elements.append(Paragraph(
            f"Matched terms: {tokens_str}", styles["small"]
        ))
    elements.append(Paragraph(exp["relevance"], styles["body"]))
    elements.append(Spacer(1, 4))

    # ── Credibility signals ───────────────────────────────────────────────
    elements.append(Paragraph("<b>Credibility signals</b>", styles["small_bold"]))
    for signal in exp["risk_signals"]:
        if signal.startswith("✓"):
            sty = styles["signal_ok"]
        elif signal.startswith("~"):
            sty = styles["signal_warn"]
        else:
            sty = styles["signal_bad"]
        elements.append(Paragraph(signal, sty))

    # ── FIX 3: Score breakdown always present, outside any wrapper ────────
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        str(exp.get("score_breakdown", "")), styles["small"]
    ))

    # ── Trend data (if available) ─────────────────────────────────────────
    trend = exp.get("trend")
    if trend and trend.get("direction"):
        direction  = trend["direction"]
        pct        = trend.get("pct")
        citations  = trend.get("citations", [])
        years      = trend.get("years", [2020,2021,2022,2023,2024])

        arrow      = "↑" if direction == "Up" else ("↓" if direction == "Down" else "→")
        color      = C_GREEN if direction == "Up" else (C_RED if direction == "Down" else C_AMBER)
        pct_str    = f"  {'+' if pct and pct > 0 else ''}{pct}%" if pct and abs(pct) < 1000 else ""

        trend_label = ParagraphStyle(
            "trend_label", fontName="Helvetica-Bold", fontSize=7.5,
            textColor=color, leading=11
        )
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(
            f"<b>Trend (2020→2024):</b> {arrow} {direction}{pct_str}",
            trend_label
        ))

        # Year-by-year citations row
        if citations and any(v is not None for v in citations):
            vals = [f"{y}: {round(c,1) if c is not None else 'N/A'}"
                    for y, c in zip(years, citations)]
            elements.append(Paragraph(
                "Citations/Doc:  " + "  →  ".join(vals),
                styles["small"]
            ))

    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=C_BORDER, spaceAfter=10
    ))

    return elements


def generate_report(explained: dict, strategy: dict, abstract: str, focus: str) -> io.BytesIO:
    """
    Generates a PDF report and returns it as a BytesIO buffer.
    Pass directly to st.download_button(data=...).
    """
    buffer  = io.BytesIO()
    styles  = build_styles()
    date_str = datetime.now().strftime("%d %B %Y")

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )

    story = []

    # ── Header ────────────────────────────────────────────────────────────
    story.append(Paragraph("Journal Recommendation Report", styles["title"]))
    if focus != "General / Best Fit":
        story.append(Paragraph(f"Domain Focus: {focus}", styles["subtitle"]))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(
        width="100%", thickness=1.5, color=C_BLUE, spaceBefore=4, spaceAfter=12
    ))

    # ── Abstract ──────────────────────────────────────────────────────────
    story.append(Paragraph("Abstract", styles["section"]))
    clean_abstract = " ".join(abstract.strip().split())
    story.append(Paragraph(clean_abstract, styles["abstract"]))
    story.append(Spacer(1, 8))

    # ── Plans ─────────────────────────────────────────────────────────────
    for plan_key in ["A", "B", "C"]:
        options = explained.get(plan_key, [])
        if not options:
            continue

        story.append(Paragraph(plan_label(plan_key), styles["section"]))
        story.append(Paragraph(plan_desc(plan_key), styles["body"]))
        story.append(Spacer(1, 6))

        for i, exp in enumerate(options, 1):
            # Flat list — no KeepTogether, so nothing gets cut off
            story.extend(render_journal(exp, i, styles))

    # ── Disclaimer ────────────────────────────────────────────────────────
    story.append(Paragraph(
        "These recommendations are AI-generated and may not always be accurate. "
        "Always verify journal scope, aims, and submission guidelines "
        "before submitting your paper.",
        styles["disclaimer"]
    ))
    story.append(Paragraph(
        "Time to publish is sourced from DOAJ and is AI-assisted — actual review and publication "
        "timelines may differ significantly depending on the journal, editor, and submission period.",
        styles["disclaimer"]
    ))
    story.append(Paragraph(f"Generated on {date_str}", styles["disclaimer"]))

    doc.build(story)
    buffer.seek(0)
    return buffer
