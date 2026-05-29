"""
STEP 5 — Final Ranking (BERT + BM25 Hybrid)
Journal Recommendation System

What this script does:
  - Uses hybrid_search (BM25 + BERT) instead of BM25-only search
  - Adds risk scores from Step 4
  - Combines hybrid relevance + safety + citation into one final_score
  - Returns a clean ranked list ready for the strategy planner

Ranking Formula (weights sum to 1.0):
  final_score = 0.50 × relevance  (hybrid_score: 40% BM25 + 60% BERT)
              + 0.30 × safety     (1 - risk, normalised)
              + 0.20 × citation   (SJR log-normalised)
"""

import pandas as pd
import math
import pickle
import numpy as np
from step4_risk_assessment import assess_risk


# ── Base weights (when no speed preference) ──────────────────────────────────
W_RELEVANCE = 0.50
W_SAFETY    = 0.30
W_CITATION  = 0.20   # prestige signal (SJR)
W_SPEED     = 0.00   # speed signal (weeks_to_publish, inverted)
# ─────────────────────────────────────────────────────────────────────────────


def load_resources():
    """
    Loads all resources needed at runtime:
      - journals_clean.csv      (journal metadata)
      - bm25_index.pkl          (BM25 inverted index)
      - journal_embeddings.npy  (BERT embeddings, shape: 29553 x 768)
      - BERT model              (for encoding the abstract at query time)
    """
    print("Loading dataset...")
    df = pd.read_csv("journals_clean.csv")
    print(f"  {len(df):,} journals loaded")

    print("Loading BM25 index...")
    with open("bm25_index.pkl", "rb") as f:
        bm25_index = pickle.load(f)

    print("Loading BERT resources...")
    from step3b_bert_rerank import load_bert_resources
    embeddings, texts, model = load_bert_resources()

    return df, bm25_index, embeddings, model


def normalise_hybrid(series: pd.Series) -> pd.Series:
    """Min-max normalise hybrid scores to [0, 1]."""
    mn, mx = series.min(), series.max()
    return (series - mn) / (mx - mn + 1e-9)


def normalise_risk(series: pd.Series) -> pd.Series:
    """Invert risk score so that low risk → high safety score [0, 1]."""
    return 1 - (series / 100)


def normalise_sjr(series: pd.Series) -> pd.Series:
    """Log-normalise SJR to compress the huge range (0 to 145)."""
    log_series = series.apply(math.log1p)
    mx = log_series.max()
    return log_series / (mx + 1e-9)


def normalise_speed(series: pd.Series) -> pd.Series:
    """
    Invert weeks_to_publish so faster = higher score.
    Journals without speed data get 0.5 (neutral).
    """
    filled = series.fillna(series.median() if series.notna().any() else 12)
    mn, mx = filled.min(), filled.max()
    raw = (filled - mn) / (mx - mn + 1e-9)
    inverted = 1 - raw   # fast journals → high score
    # Journals with no data stay at 0.5
    inverted[series.isna()] = 0.5
    return inverted


def rank(results: pd.DataFrame, focus: str = "General / Best Fit",
         prestige_weight: float = 1.0, abstract: str = "") -> pd.DataFrame:
    """
    Computes final_score and sorts journals from best to worst.

    prestige_weight: float 0.0 to 1.0
      1.0 = full prestige (SJR dominates, original behaviour)
      0.0 = full speed    (weeks_to_publish dominates)
      0.5 = balanced mix

    Relevance gate: drops any journal with hybrid_norm < MIN_RELEVANCE.
    """
    from step5c_focus_filter import apply_focus

    MIN_RELEVANCE = 0.10

    results = results.copy()
    results = apply_focus(results, focus)

    results["hybrid_norm"] = normalise_hybrid(results["adjusted_hybrid"])
    results["risk_norm"]   = normalise_risk(results["risk_score"])
    results["sjr_norm"]    = normalise_sjr(results["SJR"])
    results["speed_norm"]  = normalise_speed(results.get("weeks_to_publish",
                                             pd.Series([None]*len(results))))

    # Dynamic weights based on prestige_weight slider (0.0 = speed, 1.0 = prestige)
    w_citation = W_CITATION * prestige_weight
    w_speed    = W_CITATION * (1.0 - prestige_weight)
    # ── Domain score (before final scoring) ─────────────────────────────
    results["domain_score"] = 1.0
    if abstract:
        from step5d_domain_intent import apply_domain_intent_weighting
        results, _ = apply_domain_intent_weighting(results, abstract)

    W_DOMAIN = 0.15   # start here

    results["final_score"] = (
        0.40 * results["hybrid_norm"] +
        0.25 * results["risk_norm"]   +
        0.15 * results["sjr_norm"]    +
        0.05 * results["speed_norm"]  +
        W_DOMAIN * results["domain_score"]
    ).round(4)

    # ── Predatory penalty ─────────────────────────────────────────────────
    # Potentially Predatory journals get a 40% score reduction
    # Caution journals get a 15% reduction
    # This ensures they stay visible (for transparency) but rank lower
    if "predatory_level" in results.columns:
        results.loc[results["predatory_level"] == "Potentially Predatory", "final_score"] *= 0.60
        results.loc[results["predatory_level"] == "Caution",               "final_score"] *= 0.85
        results["final_score"] = results["final_score"].round(4)

    # ── Domain intent mismatch penalty ────────────────────────
    if abstract:
        from step5d_domain_intent import apply_domain_intent_weighting
        results, _ = apply_domain_intent_weighting(results, abstract)

    results = results.sort_values("final_score", ascending=False)

    # ── Relevance gate ────────────────────────────────────────────────────
    before = len(results)
    results = results[results["hybrid_norm"] >= MIN_RELEVANCE].copy()
    dropped = before - len(results)
    if dropped > 0:
        print(f"  Relevance gate: dropped {dropped} low-relevance journals")

    results = results.sort_values("final_score", ascending=False).reset_index(drop=True)
    results.index += 1
    results.index.name = "rank"

    return results
def display_ranked(results: pd.DataFrame):
    print(f"\n{'Rank':<5} {'Final':<7} {'Hybrid':<8} {'BERT':<7} {'Risk':<8} {'Q':<5} {'H':<6} Title")
    print("-" * 100)
    for rank, row in results.iterrows():
        risk_icon = "✓" if row["risk_level"] == "Low" else ("~" if row["risk_level"] == "Medium" else "⚠")
        print(
            f"{rank:<5} {row['final_score']:<7} {row['hybrid_score']:<8} "
            f"{row['bert_score']:<7} {risk_icon} {row['risk_level']:<6} "
            f"{row['Quartile']:<5} {int(row['H_index']):<6} {row['Title']}"
        )


def get_ranked_results(
    abstract: str, df, bm25_index, embeddings, model,
    top_n: int = 20, focus: str = "General / Best Fit",
    prestige_weight: float = 1.0
) -> pd.DataFrame:
    """
    Full hybrid pipeline: hybrid_search -> risk -> rank.
    focus:           optional domain filter
    prestige_weight: 1.0 = full prestige, 0.0 = full speed, 0.5 = balanced
    """
    from step3b_bert_rerank import hybrid_search
    candidates = hybrid_search(abstract, bm25_index, embeddings, model, df, top_n=top_n)
    assessed   = assess_risk(candidates, abstract)
    ranked = rank(assessed, focus=focus, prestige_weight=prestige_weight, abstract=abstract)
    return ranked


def main():
    print("\n=== STEP 5: Final Ranking (Hybrid BM25 + BERT) ===\n")

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
        {
            "label": "Environmental Science / Climate",
            "text": """
                This study investigates the impact of rising sea surface temperatures on
                coral reef bleaching events in the Indo-Pacific region. Remote sensing data
                combined with in-situ measurements reveal accelerating bleaching frequency
                correlated with El Nino cycles and anthropogenic CO2 emissions.
            """
        },
    ]

    for abstract in abstracts:
        print(f"\n{'='*100}")
        print(f"ABSTRACT: {abstract['label']}")
        print(f"{'='*100}")
        results = get_ranked_results(abstract["text"], df, bm25_index, embeddings, model, top_n=20)
        display_ranked(results.head(10))

    print("\n✓ Step 5 complete. Run step6_strategy.py next.\n")


if __name__ == "__main__":
    main()
