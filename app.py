"""
STEP 8 — Streamlit Web App
Journal Recommendation System

Run with:
    streamlit run app.py

Required files in same folder:
    journals_clean.csv
    bm25_index.pkl
    step2_build_index.py  (for score_query)
    step3_query.py
    step4_risk_assessment.py
    step5_ranking.py
    step6_strategy.py
    step7_explain.py
"""

import streamlit as st
import pandas as pd

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JournalFinder",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Reset & base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0b0f1a;
    color: #e8e6e0;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem 3rem; max-width: 1200px; }

/* ── Hero ── */
.hero {
    padding: 3.5rem 0 2rem 0;
    border-bottom: 1px solid #1e2535;
    margin-bottom: 2.5rem;
}
.hero-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #5a8aff;
    margin-bottom: 0.8rem;
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 3.2rem;
    font-weight: 800;
    line-height: 1.05;
    color: #f0ede6;
    margin-bottom: 0.8rem;
}
.hero-title span { color: #5a8aff; }
.hero-sub {
    font-size: 1rem;
    color: #7a8399;
    font-weight: 300;
    max-width: 560px;
}

/* ── Textarea ── */
.stTextArea textarea {
    background: #111624 !important;
    border: 1px solid #1e2840 !important;
    border-radius: 10px !important;
    color: #e8e6e0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.92rem !important;
    padding: 1rem !important;
    resize: vertical !important;
}
.stTextArea textarea:focus {
    border-color: #5a8aff !important;
    box-shadow: 0 0 0 2px rgba(90,138,255,0.15) !important;
}

/* ── Button ── */
.stButton > button {
    background: #5a8aff !important;
    color: #0b0f1a !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.06em !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.65rem 2rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #7aa3ff !important;
    transform: translateY(-1px) !important;
}

/* ── Plan tabs ── */
.plan-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1.2rem 1.5rem;
    border-radius: 10px 10px 0 0;
    margin-bottom: 0;
}
.plan-a { background: linear-gradient(135deg, #1a2340, #0f1a35); border-left: 3px solid #5a8aff; }
.plan-b { background: linear-gradient(135deg, #1a2a20, #0f1f16); border-left: 3px solid #4caf82; }
.plan-c { background: linear-gradient(135deg, #2a2010, #1f1608); border-left: 3px solid #c49a3c; }

.plan-badge {
    font-family: 'Syne', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
}
.badge-a { background: rgba(90,138,255,0.15); color: #5a8aff; }
.badge-b { background: rgba(76,175,130,0.15); color: #4caf82; }
.badge-c { background: rgba(196,154,60,0.15);  color: #c49a3c; }

.plan-title {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: #f0ede6;
}
.plan-desc {
    font-size: 0.82rem;
    color: #6a7490;
    margin-left: auto;
}

/* ── Journal card ── */
.journal-card {
    background: #111624;
    border: 1px solid #1e2535;
    border-radius: 0 0 10px 10px;
    padding: 1.4rem 1.5rem;
    margin-bottom: 1.5rem;
}
.journal-card + .journal-card {
    border-radius: 10px;
    margin-top: 0.5rem;
}

.card-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
}
.card-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    color: #f0ede6;
    line-height: 1.3;
    flex: 1;
    padding-right: 1rem;
}
.card-score {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    color: #5a8aff;
    white-space: nowrap;
}

.tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 1rem;
}
.tag {
    font-size: 0.7rem;
    font-weight: 500;
    padding: 0.18rem 0.55rem;
    border-radius: 4px;
    letter-spacing: 0.04em;
}
.tag-q1 { background: rgba(90,138,255,0.12); color: #5a8aff; border: 1px solid rgba(90,138,255,0.25); }
.tag-q2 { background: rgba(76,175,130,0.12); color: #4caf82; border: 1px solid rgba(76,175,130,0.25); }
.tag-q3 { background: rgba(196,154,60,0.12);  color: #c49a3c; border: 1px solid rgba(196,154,60,0.25); }
.tag-q4 { background: rgba(180,80,80,0.12);   color: #e07070; border: 1px solid rgba(180,80,80,0.25); }
.tag-oa  { background: rgba(76,175,130,0.1);  color: #4caf82; border: 1px solid rgba(76,175,130,0.2); }
.tag-low  { background: rgba(76,175,130,0.1);  color: #4caf82; border: 1px solid rgba(76,175,130,0.2); }
.tag-med  { background: rgba(196,154,60,0.1);  color: #c49a3c; border: 1px solid rgba(196,154,60,0.2); }
.tag-high { background: rgba(180,80,80,0.1);   color: #e07070; border: 1px solid rgba(180,80,80,0.2); }

.meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
    margin-bottom: 1rem;
    font-size: 0.82rem;
    color: #6a7490;
}
.meta-item strong { color: #aab0c0; font-weight: 500; }

/* ── Explanation box ── */
.explain-box {
    background: #0d1120;
    border: 1px solid #1a2030;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-top: 0.8rem;
}
.explain-section {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #3d4a66;
    margin-bottom: 0.4rem;
    margin-top: 0.8rem;
}
.explain-section:first-child { margin-top: 0; }
.explain-text {
    font-size: 0.85rem;
    color: #8892a8;
    line-height: 1.6;
}
.signal-ok   { color: #4caf82; font-size: 0.83rem; line-height: 1.8; }
.signal-warn { color: #c49a3c; font-size: 0.83rem; line-height: 1.8; }
.signal-bad  { color: #e07070; font-size: 0.83rem; line-height: 1.8; }
.score-breakdown {
    font-size: 0.78rem;
    color: #4a5570;
    font-family: 'DM Mono', monospace;
    margin-top: 0.5rem;
    padding-top: 0.6rem;
    border-top: 1px solid #1a2030;
}

/* ── Stats row ── */
.stats-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 2.5rem;
}
.stat-box {
    flex: 1;
    background: #111624;
    border: 1px solid #1e2535;
    border-radius: 10px;
    padding: 1.1rem 1.3rem;
    text-align: center;
}
.stat-num {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    color: #5a8aff;
}
.stat-label {
    font-size: 0.72rem;
    color: #4a5570;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 0.2rem;
}

/* ── Tokens ── */
.token-chip {
    display: inline-block;
    background: rgba(90,138,255,0.1);
    border: 1px solid rgba(90,138,255,0.2);
    color: #5a8aff;
    font-size: 0.72rem;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    margin: 0.15rem;
}

/* ── Divider ── */
.section-divider {
    border: none;
    border-top: 1px solid #1e2535;
    margin: 2rem 0;
}

/* ── Spinner override ── */
.stSpinner > div { border-top-color: #5a8aff !important; }
</style>
""", unsafe_allow_html=True)


# ── Load resources (cached) ───────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_all():
    from step5_ranking import load_resources
    df, bm25_index, embeddings, model = load_resources()
    return df, bm25_index, embeddings, model


# ── Helpers ───────────────────────────────────────────────────────────────────
def quartile_tag(q):
    cls = {"Q1": "tag-q1", "Q2": "tag-q2", "Q3": "tag-q3", "Q4": "tag-q4"}.get(q, "tag-q4")
    return f'<span class="tag {cls}">{q}</span>'


def risk_tag(r):
    cls = {"Low": "tag-low", "Medium": "tag-med", "High": "tag-high"}.get(r, "tag-med")
    return f'<span class="tag {cls}">Risk: {r}</span>'


def apc_tag(exp):
    apc_usd = exp.get("apc_usd")
    apc_amt = exp.get("apc_amount")
    oa      = str(exp.get("open_access","")).strip()

    if oa != "Yes":
        return ""
    if apc_amt == 0:
        return '<span class="tag tag-oa">Free OA</span>'
    if apc_usd and apc_usd > 0:
        return f'<span class="tag tag-med">APC ~${int(apc_usd):,}</span>'
    return '<span class="tag tag-oa">Open Access</span>'


def signal_html(s):
    if s.startswith("✓"):
        return f'<div class="signal-ok">{s}</div>'
    elif s.startswith("~"):
        return f'<div class="signal-warn">{s}</div>'
    else:
        return f'<div class="signal-bad">{s}</div>'


def render_journal_card(exp, plan_color, option_num):
    oa_tag    = apc_tag(exp)
    score_pct = int(exp["final_score"] * 100)
    sp = "\u00a0"  # unicode non-breaking space — avoids &nbsp; escaping issues

    # ── Card header ──
    st.markdown(
        f'<div class="journal-card">',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div class="card-top">'
        f'<div class="card-title">#{option_num}{sp}{sp}{exp["title"]}</div>'
        f'<div class="card-score">{score_pct}'
        f'<span style="font-size:1rem;color:#3d4a66">%</span></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Tags ──
    st.markdown(
        f'<div class="tags">{quartile_tag(exp["quartile"])}'
        f'{risk_tag(exp["risk_level"])}{oa_tag}</div>',
        unsafe_allow_html=True
    )

    # ── Meta rows ──
    cs = exp.get("citescore")
    if_val = exp.get("impact_factor")
    extra_metrics = ""
    if cs is not None:
        extra_metrics += f'<div class="meta-item"><strong>CiteScore</strong>{sp}{cs}</div>'
    if if_val is not None:
        extra_metrics += f'<div class="meta-item"><strong>Impact Factor</strong>{sp}{if_val}</div>'

    st.markdown(
        f'<div class="meta-row">'
        f'<div class="meta-item"><strong>H-index</strong>{sp}{exp["h_index"]}</div>'
        f'<div class="meta-item"><strong>SJR</strong>{sp}{exp["sjr"]}</div>'
        f'{extra_metrics}'
        f'<div class="meta-item"><strong>Publisher</strong>{sp}{exp["publisher"]}</div>'
        f'<div class="meta-item"><strong>Coverage</strong>{sp}{exp["coverage"]}</div>'
        f'<div class="meta-item"><strong>ISSN</strong>{sp}{exp["issn"]}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div class="meta-row" style="margin-bottom:0">'
        f'<div class="meta-item"><strong>Areas</strong>{sp}{exp["areas"]}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Explanation box ──
    tokens_html = ""
    if exp["matched_tokens"]:
        chips = "".join(f'<span class="token-chip">{t}</span>' for t in exp["matched_tokens"])
        tokens_html = f'<div style="margin-bottom:0.6rem">{chips}</div>'

    signals_html = "".join(signal_html(s) for s in exp["risk_signals"])

    st.markdown(
        f'<div class="explain-box">'
        f'<div class="explain-section">Why recommended</div>'
        f'{tokens_html}'
        f'<div class="explain-text">{exp["relevance"]}</div>'
        f'<div class="explain-section">Credibility signals</div>'
        f'{signals_html}'
        f'<div class="score-breakdown">{exp["score_breakdown"]}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)


def render_plan(plan_key, explained, meta, header_cls, badge_cls, timeline):
    options = explained.get(plan_key, [])
    color_map = {"A": "#5a8aff", "B": "#4caf82", "C": "#c49a3c"}
    color = color_map[plan_key]

    st.markdown(
        f'<div class="plan-header {header_cls}">'
        f'<span class="plan-badge {badge_cls}">{plan_key}</span>'
        f'<span class="plan-title">{meta["label"]}</span>'
        f'<span class="plan-desc">{timeline}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    if not options:
        st.markdown(
            '<div class="journal-card" style="color:#4a5570">No journals found for this plan.</div>',
            unsafe_allow_html=True
        )
        return

    for i, exp in enumerate(options, 1):
        render_journal_card(exp, color, i)


# ── Main UI ───────────────────────────────────────────────────────────────────
def main():

    # Hero
    st.markdown("""
    <div class="hero">
        <div class="hero-label">AI-Powered Academic Tool</div>
        <div class="hero-title">Find the right<br><span>journal</span> for your paper.</div>
        <div class="hero-sub">Paste your abstract. Get ranked, risk-assessed journal recommendations with a full submission strategy.</div>
    </div>
    """, unsafe_allow_html=True)

    # Input
    abstract = st.text_area(
        "Paper Abstract",
        placeholder="Paste your paper abstract here...",
        height=180,
        label_visibility="collapsed",
    )

    col1, col2, col3 = st.columns([1, 2, 3])
    with col1:
        search_clicked = st.button("Find Journals →")
    with col2:
        from step5c_focus_filter import FOCUS_OPTIONS
        focus = st.selectbox(
            "Domain Focus",
            FOCUS_OPTIONS,
            index=0,
            label_visibility="collapsed",
            help="Optionally boost journals from a specific domain. General = no boost."
        )

    if not search_clicked:
        st.markdown("""
        <div style="margin-top:3rem;padding:2rem;background:#0d1120;border:1px solid #1a2030;
                    border-radius:12px;text-align:center;color:#3d4a66">
            <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;
                        color:#2a3450;margin-bottom:0.5rem">29,553 journals indexed</div>
            <div style="font-size:0.82rem">Enter your abstract above to get started</div>
        </div>
        """, unsafe_allow_html=True)
        return

    if not abstract.strip():
        st.error("Please paste your abstract before searching.")
        return

    # Abstract length warning
    word_count = len(abstract.split())
    if word_count < 30:
        st.warning(
            f"Your abstract is very short ({word_count} words). "
            "BERT needs at least 30 words to detect meaning accurately. "
            "Results may be less reliable — consider pasting the full abstract."
        )
    elif word_count < 60:
        st.info(
            f"Abstract is {word_count} words. For best results, "
            "a full abstract (100–250 words) gives BERT more context to work with."
        )

    # Run pipeline
    with st.spinner("Searching 29,553 journals..."):
        try:
            df_full, bm25_index, embeddings, model = load_all()
            from step6_strategy import build_strategy, PLAN_META
            from step7_explain import explain_strategy
            from step3b_bert_rerank import tokenize

            strategy  = build_strategy(abstract, df_full, bm25_index, embeddings, model, focus=focus)
            explained = explain_strategy(strategy, abstract, df_full)

        except Exception as e:
            st.error(f"Error: {e}")
            return

    # Focus badge
    from step5c_focus_filter import FOCUS_CONFIG
    if focus != "General / Best Fit":
        focus_desc = FOCUS_CONFIG[focus]["description"]
        st.markdown(
            f'<div style="background:rgba(90,138,255,0.08);border:1px solid rgba(90,138,255,0.2);'
            f'border-radius:8px;padding:0.6rem 1rem;margin-bottom:1rem;font-size:0.83rem;color:#7aa3ff">'
            f'<strong>Focus: {focus}</strong> — {focus_desc}</div>',
            unsafe_allow_html=True
        )

    # Stats row
    ranked   = strategy["ranked"]
    total    = len(ranked)
    low_risk = (ranked["risk_level"] == "Low").sum()
    q1_count = (ranked["Quartile"] == "Q1").sum()
    tokens   = tokenize(abstract)

    st.markdown(
        f'<div class="stats-row">'
        f'<div class="stat-box"><div class="stat-num">{total}</div><div class="stat-label">Candidates found</div></div>'
        f'<div class="stat-box"><div class="stat-num">{q1_count}</div><div class="stat-label">Q1 journals</div></div>'
        f'<div class="stat-box"><div class="stat-num">{low_risk}</div><div class="stat-label">Low-risk options</div></div>'
        f'<div class="stat-box"><div class="stat-num">{len(tokens)}</div><div class="stat-label">Query terms</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Plans
    plans_config = [
        ("A", "plan-a", "badge-a", PLAN_META["A"]["description"]),
        ("B", "plan-b", "badge-b", PLAN_META["B"]["description"]),
        ("C", "plan-c", "badge-c", PLAN_META["C"]["description"]),
    ]

    for plan_key, header_cls, badge_cls, timeline in plans_config:
        render_plan(plan_key, explained, PLAN_META[plan_key], header_cls, badge_cls, timeline)
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # ── PDF Download ──────────────────────────────────────────────────────
    try:
        from generate_pdf import generate_report
        pdf_buf = generate_report(explained, strategy, abstract, focus)
        date_str = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            label="Download Report as PDF",
            data=pdf_buf,
            file_name=f"journal_recommendations_{date_str}.pdf",
            mime="application/pdf",
        )
    except Exception as e:
        st.caption(f"PDF generation unavailable: {e}")

    st.markdown(
        '<div style="text-align:center;color:#3d4a66;font-size:0.78rem;padding:0.5rem 0 0.3rem 0">'
        'These recommendations are AI-generated and may not always be accurate. '
        'Always verify journal scope, aims, and submission guidelines before submitting your paper.'
        '</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div style="text-align:center;color:#3d4a66;font-size:0.78rem;padding:0 0 0.3rem 0">'
        'APC values are sourced from DOAJ and converted to USD using approximate exchange rates. '
        'Actual charges may differ — always confirm on the journal official website before submitting.'
        '</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div style="text-align:center;color:#3d4a66;font-size:0.78rem;padding:0 0 2rem 0">'
        'Time to publish is sourced from DOAJ and is AI-assisted — actual review and publication '
        'timelines may differ significantly depending on the journal, editor, and submission period.'
        '</div>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
