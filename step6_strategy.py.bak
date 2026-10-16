"""
STEP 6 — Submission Strategy Planner
Journal Recommendation System

What this script does:
  - Takes the final ranked list from Step 5
  - Assigns journals into three strategic plans
  - Adds submission advice and timeline estimates per plan

Plan Assignment Logic:
  Plan A — Ambitious  : Q1 journals, risk != High  (top-tier, competitive)
  Plan B — Balanced   : Q2 journals, risk != High  (realistic target)
  Plan C — Safe       : Best remaining non-High-risk journals by final_score

Each plan returns up to 3 journal options, ranked by final_score within the plan.
"""

import pandas as pd
from step5_ranking import get_ranked_results, load_resources


# ── Plan metadata ─────────────────────────────────────────────────────────────
PLAN_META = {
    "A": {
        "label":       "Plan A — Ambitious",
        "quartile":    "Q1",
        "description": "Top-tier journals. High competition but maximum academic impact if accepted.",
        "advice":      "Submit here first. If rejected, use reviewer feedback "
                       "to strengthen the paper before moving to Plan B.",
    },
    "B": {
        "label":       "Plan B — Balanced",
        "quartile":    "Q2",
        "description": "Strong, well-regarded journals with a higher acceptance "
                       "rate than Q1. Good balance of prestige and realism.",
        "advice":      "A solid target if Plan A is too competitive for the "
                       "paper's current scope. Good citation visibility.",
    },
    "C": {
        "label":       "Plan C — Safe Fallback",
        "quartile":    "Q3/Q4",
        "description": "Lower-tier but indexed journals. Useful when publication speed matters.",
        "advice":      "Use only if Plans A and B are rejected, or if a fast "
                       "publication deadline is a priority.",
    },
}


def publication_frequency(docs_2024: float, docs_3years: float) -> str:
    """
    Returns a data-driven publication volume label for a journal.
    Based on actual docs published — not guessed review times.
    Thresholds derived from dataset percentiles:
      bottom 25% < 22/year, top 25% > 95/year
    """
    annual = int(docs_2024) if docs_2024 > 0 else round(docs_3years / 3)
    if annual == 0:
        return "Volume: unknown — no recent publication data"
    elif annual < 22:
        return f"~{annual} papers/year — low volume, selective"
    elif annual < 95:
        return f"~{annual} papers/year — moderate volume"
    else:
        return f"~{annual} papers/year — high volume, active journal"


def assign_plans(results: pd.DataFrame) -> dict:
    """
    Splits ranked results into three strategic plans.
    Guarantees at least 1 journal per plan using fallbacks.
    Plan C excludes High-risk journals to avoid predatory recommendations.
    """
    plan_a, plan_b, plan_c = [], [], []

    for _, row in results.iterrows():
        q = row["Quartile"]
        r = row["risk_level"]

        if q == "Q1" and r != "High":
            plan_a.append(row)
        elif q == "Q2" and r != "High":
            plan_b.append(row)
        elif q in ["Q3", "Q4", "Unranked"] and r != "High":
            plan_c.append(row)
        # High-risk journals are excluded from all plans

    # Fallback: if a plan is empty, pull the best unused ranked journal
    assigned_titles = (
        {r["Title"] for r in plan_a} |
        {r["Title"] for r in plan_b} |
        {r["Title"] for r in plan_c}
    )

    fallback_pool = [
        row for _, row in results.iterrows()
        if row["Title"] not in assigned_titles and row["risk_level"] != "High"
    ]

    if not plan_a and fallback_pool:
        plan_a.append(fallback_pool.pop(0))
    if not plan_b and fallback_pool:
        plan_b.append(fallback_pool.pop(0))
    if not plan_c and fallback_pool:
        plan_c.append(fallback_pool.pop(0))

    return {
        "A": pd.DataFrame(plan_a).reset_index(drop=True),
        "B": pd.DataFrame(plan_b).reset_index(drop=True),
        "C": pd.DataFrame(plan_c).reset_index(drop=True),
    }


def build_strategy(abstract: str, df, bm25_index, embeddings, model,
                    focus: str = "General / Best Fit",
                    prestige_weight: float = 1.0) -> dict:
    """
    Full pipeline entry point for the strategy planner.
    focus: optional domain filter passed through to ranking.
    Returns a dict with plans A, B, C and their metadata.
    """
    ranked = get_ranked_results(abstract, df, bm25_index, embeddings, model,
                                top_n=30, focus=focus, prestige_weight=prestige_weight)
    plans  = assign_plans(ranked)

    return {
        "plans":  plans,
        "ranked": ranked,
        "focus":  focus,
    }


def display_strategy(strategy: dict):
    plans  = strategy["plans"]

    for key in ["A", "B", "C"]:
        meta = PLAN_META[key]
        plan = plans[key]

        print(f"\n{'─'*80}")
        print(f"  {meta['label']}  ({meta['quartile']})")
        print(f"  {meta['description']}")
        print(f"  Advice: {meta['advice']}")
        print(f"{'─'*80}")

        if plan.empty:
            print("  No suitable journals found for this plan.")
            continue

        for i, row in plan.iterrows():
            oa_tag = " [Open Access]" if str(row["Open_Access"]).strip() == "Yes" else ""
            print(f"\n  Option {i+1}: {row['Title']}{oa_tag}")
            print(f"    Quartile : {row['Quartile']}  |  H-index: {int(row['H_index'])}"
                  f"  |  SJR: {row['SJR']}  |  Risk: {row['risk_level']}")
            print(f"    Publisher: {row['Publisher']}")
            print(f"    Areas    : {row['Areas']}")
            print(f"    Coverage : {row['Coverage']}")
            print(f"    Score    : {row['final_score']} (relevance + safety + citation)")


def main():
    print("\n=== STEP 6: Submission Strategy Planner ===\n")

    df, bm25_index, embeddings, model = load_resources()

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
        print(f"\n{'='*80}")
        print(f"ABSTRACT: {abstract['label']}")
        print(f"{'='*80}")
        strategy = build_strategy(abstract["text"], df, bm25_index, embeddings, model, focus="General / Best Fit")
        display_strategy(strategy)

    print("\n\n✓ Step 6 complete. Run step7_explain.py next.\n")


if __name__ == "__main__":
    main()
