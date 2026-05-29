"""
STEP 7 — Explainable Output
Journal Recommendation System

What this script does:
  - Takes each journal from the strategy plans
  - Generates a human-readable explanation for why it was recommended
  - Every explanation is built dynamically from live data:
      * Which abstract tokens matched this journal
      * Which risk dimensions flagged it and why
      * Exact score breakdown (relevance / safety / citation)

Nothing is hardcoded — change the abstract, the explanation changes too.
"""

import pandas as pd
import re
from step3b_bert_rerank import tokenize
from step6_strategy import build_strategy, PLAN_META


# ── Explanation builders ──────────────────────────────────────────────────────

def get_matched_tokens(row: pd.Series, abstract_tokens: set, df_full: pd.DataFrame) -> list:
    """Find which abstract tokens actually appear in the journal's indexed text."""
    journal_text = df_full.iloc[int(row["doc_id"])]["journal_text"]
    journal_tokens = set(re.findall(r"[a-z]+", str(journal_text)))
    return sorted([t for t in abstract_tokens if t in journal_tokens and len(t) > 4])


def explain_relevance(matched_tokens: list, hybrid_score: float, hybrid_norm: float,
                      bert_score: float, bm25_score: float) -> str:
    """
    Explain why the journal is relevant.
    Detects three cases:
      1. Strong keyword + semantic match  → standard explanation
      2. High BERT but low BM25          → contextual bridge (interdisciplinary)
      3. No match at all                 → honest warning
    """
    # Contextual bridge: BERT sees meaning even when keywords differ
    bert_high  = bert_score > 0.80
    bm25_low   = bm25_score < 3.0

    if bert_high and bm25_low and not matched_tokens:
        return (
            "Recommended for conceptual alignment rather than keyword overlap. "
            "The semantic model detected thematic similarity between your abstract "
            "and this journal's scope — likely due to shared underlying concepts "
            "across disciplines. Verify the journal's aim and scope manually."
        )

    if matched_tokens:
        words    = ", ".join(f'"{t}"' for t in matched_tokens[:6])
        strength = "strong" if hybrid_norm > 0.6 else ("moderate" if hybrid_norm > 0.3 else "weak")

        # Add bridge note if BERT is also contributing strongly
        bridge = ""
        if bert_high and len(matched_tokens) <= 2:
            bridge = (" The semantic model also detected broader conceptual overlap "
                      "beyond the matched keywords.")

        return (f"{strength.capitalize()} topic match. "
                f"Your abstract shares key terms with this journal: {words}.{bridge}")

    return ("No direct keyword overlap found with journal title or categories. "
            "Ranked by structural similarity — verify scope manually.")


def explain_risk(row: pd.Series) -> list:
    """Return a list of risk signal sentences based on penalty values."""
    signals = []

    # SJR
    p = row["penalty_sjr"]
    if p == 0:
        signals.append(f"✓ Strong citation influence (SJR: {row['SJR']}).")
    elif p <= 10:
        signals.append(f"~ Moderate citation influence (SJR: {row['SJR']}).")
    else:
        signals.append(f"⚠ Low citation influence (SJR: {row['SJR']}) — consider impact on visibility.")

    # H-index
    p = row["penalty_h_index"]
    h = int(row["H_index"])
    if p == 0:
        signals.append(f"✓ High academic standing (H-index: {h}).")
    elif p <= 10:
        signals.append(f"~ Acceptable academic standing (H-index: {h}).")
    else:
        signals.append(f"⚠ Low H-index ({h}) — journal may have limited visibility.")

    # Longevity
    p = row["penalty_longevity"]
    cov = row["Coverage"]
    if p == 0:
        signals.append(f"✓ Well-established journal (Coverage: {cov}).")
    elif p <= 10:
        signals.append(f"~ Moderately established (Coverage: {cov}).")
    else:
        signals.append(f"⚠ Recently indexed or short coverage period ({cov}) — limited track record.")

    # Publisher
    p = row["penalty_publisher"]
    pub = row["Publisher"]
    if p == 0:
        signals.append(f"✓ Reputable publisher: {pub}.")
    elif p == 10:
        signals.append(f"~ Publisher not in top-tier list but appears legitimate: {pub}.")
    else:
        signals.append(f"⚠ Publisher unknown or unverified: {pub}.")

    # Domain match
    p = row["penalty_domain"]
    if p == 0:
        signals.append(f"✓ Journal area aligns with abstract domain ({row['Areas']}).")
    elif p <= 10:
        signals.append(f"~ Partial area alignment ({row['Areas']}).")
    else:
        signals.append(f"⚠ Journal area ({row['Areas']}) does not clearly match abstract domain.")

    return signals


def explain_score(row: pd.Series) -> str:
    """Show the score breakdown as percentages."""
    rel  = round(row["hybrid_norm"] * 0.50, 4)
    safe = round(row["risk_norm"]  * 0.30, 4)
    cite = round(row["sjr_norm"]   * 0.20, 4)
    total = row["final_score"]

    return (f"Score breakdown → "
            f"Relevance: {rel} (50%) + "
            f"Safety: {safe} (30%) + "
            f"Citation: {cite} (20%) = {total}")


def explain_journal(row: pd.Series, abstract_tokens: set, df_full: pd.DataFrame) -> dict:
    """
    Master function — generates the full explanation for one journal.
    Returns a dict used by both terminal display and Streamlit UI.
    """
    matched  = get_matched_tokens(row, abstract_tokens, df_full)
    relevance_text = explain_relevance(
        matched, row["hybrid_score"], row["hybrid_norm"],
        row["bert_score"], row["bm25_score"]
    )
    risk_signals   = explain_risk(row)
    score_text     = explain_score(row)

    return {
        "title":          row["Title"],
        "quartile":       row["Quartile"],
        "risk_level":     row["risk_level"],
        "final_score":    row["final_score"],
        "matched_tokens": matched,
        "relevance":      relevance_text,
        "risk_signals":   risk_signals,
        "score_breakdown":score_text,
        "open_access":    row["Open_Access"],
        "publisher":      row["Publisher"],
        "areas":          row["Areas"],
        "coverage":       row["Coverage"],
        "h_index":        int(row["H_index"]),
        "sjr":            row["SJR"],
        "issn":           row["Issn"],
        "apc_usd":        row.get("apc_usd",      None),
        "apc_currency":   row.get("apc_currency",  None),
        "apc_amount":     row.get("apc_amount",    None),
        "apc_url":        row.get("apc_url",       None),
        "citescore":      row.get("citescore",     None),
        "impact_factor":  row.get("impact_factor", None),
        "trend":            row.get("trend",            None),
        "weeks_to_publish":   row.get("weeks_to_publish",   None),
        "months_to_publish":  row.get("months_to_publish",  None),
        "in_doaj":            row.get("in_doaj",            False),
        "predatory_score":    row.get("predatory_score",    0),
        "predatory_level":    row.get("predatory_level",    "Clear"),
        "predatory_flags":    row.get("predatory_flags",    []),
    }


def explain_strategy(strategy: dict, abstract: str, df_full: pd.DataFrame) -> dict:
    """
    Generates explanations for all journals across all three plans.
    Returns a nested dict: {plan_key: [explanation_dict, ...]}
    Used directly by the Streamlit app in Step 8.
    """
    abstract_tokens = set(tokenize(abstract))
    explained = {}

    for plan_key, plan_df in strategy["plans"].items():
        explained[plan_key] = []
        for _, row in plan_df.iterrows():
            exp = explain_journal(row, abstract_tokens, df_full)
            explained[plan_key].append(exp)

    return explained


# ── Display ───────────────────────────────────────────────────────────────────

def display_explanations(explained: dict):
    for plan_key in ["A", "B", "C"]:
        meta    = PLAN_META[plan_key]
        options = explained.get(plan_key, [])

        print(f"\n{'═'*80}")
        print(f"  {meta['label']}")
        print(f"{'═'*80}")

        if not options:
            print("  No journals assigned to this plan.")
            continue

        for i, exp in enumerate(options, 1):
            oa = " [Open Access]" if str(exp["open_access"]).strip() == "Yes" else ""
            print(f"\n  Option {i}: {exp['title']}{oa}")
            print(f"  {'─'*60}")
            print(f"  Quartile : {exp['quartile']}  |  H-index: {exp['h_index']}"
                  f"  |  SJR: {exp['sjr']}  |  Risk: {exp['risk_level']}")
            print(f"  ISSN     : {exp['issn']}")
            print()
            print(f"  WHY RECOMMENDED")
            print(f"  {exp['relevance']}")
            print()
            print(f"  CREDIBILITY SIGNALS")
            for signal in exp["risk_signals"]:
                print(f"    {signal}")
            print()
            print(f"  {exp['score_breakdown']}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n=== STEP 7: Explainable Output ===\n")

    from step5_ranking import load_resources
    df_full, bm25_index, embeddings, model = load_resources()

    abstracts = [
        {
            "label": "Medical AI / Diabetic Retinopathy",
            "text": """
                This paper proposes a deep learning framework for early detection of diabetic
                retinopathy using convolutional neural networks. We analyze retinal fundus images
                and classify severity levels using transfer learning on ResNet50. The model
                achieves 94% accuracy on the APTOS dataset and outperforms existing methods
                in sensitivity and specificity.
            """
        },
        {
            "label": "Economics / Game Theory",
            "text": """
                We examine Nash equilibrium strategies in multi-player auction mechanisms.
                Using mechanism design theory, we derive conditions under which truthful
                bidding constitutes a dominant strategy equilibrium. Applications to
                spectrum auctions and public goods procurement are discussed.
            """
        },
    ]

    for abstract in abstracts:
        print(f"\n{'#'*80}")
        print(f"  ABSTRACT: {abstract['label']}")
        print(f"{'#'*80}")

        strategy  = build_strategy(abstract["text"], df_full, bm25_index, embeddings, model)
        explained = explain_strategy(strategy, abstract["text"], df_full)
        display_explanations(explained)

    print("\n\n✓ Step 7 complete. Ready for Step 8 — Streamlit app.\n")


if __name__ == "__main__":
    main()
