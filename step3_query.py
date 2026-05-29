"""
STEP 3 — Query Processing
Journal Recommendation System

What this script does:
  - Loads bm25_index.pkl and journals_clean.csv
  - Accepts a paper abstract as input
  - Tokenizes and cleans the abstract (stopword removal)
  - Scores all journals using BM25
  - Returns top N candidate journals with key metadata

NOTE: The STOPWORDS list and tokenize() function must stay identical
      in both this file and step2_build_index.py — the index was built
      with the same tokenizer, so queries must use the same one.
"""

import pandas as pd
import pickle
import re
import math
from collections import defaultdict


# ── Config ────────────────────────────────────────────────────────────────────
INDEX_FILE   = "bm25_index.pkl"
DATASET_FILE = "journals_clean.csv"
TOP_N        = 20     # number of candidate journals to retrieve
K1           = 1.5
B            = 0.75
# ─────────────────────────────────────────────────────────────────────────────


# Words that carry no domain signal — removed from both index and queries
STOPWORDS = {
    "the","a","an","and","or","of","in","on","for","to","is","are","was",
    "were","be","been","being","have","has","had","do","does","did","will",
    "would","could","should","may","might","can","this","that","these",
    "those","we","our","their","its","it","as","by","with","from","at",
    "using","used","use","based","paper","proposed","method","methods",
    "approach","results","show","shows","also","well","than","more","which",
    "both","between","into","such","each","however","while","among","within",
    "across","through","after","about","over","under","new","two","three",
    "high","low","large","small","data","model","models","system","systems",
    "learning","performance","framework","propose","present","achieve",
    "accuracy","dataset","existing","outperform","evaluate","evaluation",
    "experiment","experiments","train","training","test","testing","compare",
    "comparison","demonstrate","analysis","analyze","study","research","work",
    "task","tasks","problem","problems","feature","features","algorithm",
    "algorithms","network","networks","layer","layers","image","images",
    "classification","classifying","classify","detection","detecting",
    "prediction","predicting","predict","improvement","improve","improved",
    "benchmark","state","art","level","levels","achieve","achieves","achieved",
    "show","shown","significant","significantly","proposed","approach"
}


def tokenize(text: str) -> list[str]:
    """
    Lowercase, extract alphabetic tokens, remove stopwords and short tokens.
    Must match the tokenizer used in step2_build_index.py exactly.
    """
    tokens = re.findall(r"[a-z]+", str(text).lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 3]


def load_resources():
    """Load the BM25 index and the journal dataframe."""
    print(f"Loading index: {INDEX_FILE}")
    with open(INDEX_FILE, "rb") as f:
        index = pickle.load(f)

    print(f"Loading dataset: {DATASET_FILE}")
    df = pd.read_csv(DATASET_FILE)

    print(f"  {index['N']:,} journals indexed\n")
    return index, df


def search(abstract: str, index: dict, df: pd.DataFrame, top_n: int = TOP_N) -> pd.DataFrame:
    """
    Score all journals against the abstract using BM25.
    Returns a DataFrame of the top_n results with key columns.
    """
    tokens = tokenize(abstract)

    if not tokens:
        print("Warning: no meaningful tokens found in abstract after filtering.")
        return pd.DataFrame()

    inverted   = index["inverted_index"]
    doc_lengths = index["doc_lengths"]
    avgdl      = index["avgdl"]
    N          = index["N"]

    scores = defaultdict(float)

    for term in tokens:
        if term not in inverted:
            continue
        posting_list = inverted[term]
        df_t = len(posting_list)
        idf  = math.log((N - df_t + 0.5) / (df_t + 0.5) + 1)

        for doc_id, freq in posting_list:
            dl = doc_lengths[doc_id]
            tf = (freq * (K1 + 1)) / (freq + K1 * (1 - B + B * dl / avgdl))
            scores[doc_id] += idf * tf

    # Sort and take top N
    top_results = sorted(scores.items(), key=lambda x: -x[1])[:top_n]

    # Build results dataframe
    rows = []
    for doc_id, score in top_results:
        row = df.iloc[doc_id]
        rows.append({
            "doc_id":      doc_id,
            "bm25_score":  round(score, 4),
            "Title":       row["Title"],
            "Publisher":   row["Publisher"],
            "SJR":         row["SJR"],
            "Quartile":    row["SJR Best Quartile"],
            "H_index":     row["H index"],
            "Citations":   row["Citations / Doc. (2years)"],
            "Open_Access": row["Open Access"],
            "Country":     row["Country"],
            "Coverage":    row["Coverage"],
            "Categories":  row["Categories"],
            "Areas":       row["Areas"],
            "Issn":        row["Issn"],
        })

    return pd.DataFrame(rows)


def display_results(results: pd.DataFrame, tokens: list[str]):
    """Pretty-print results to terminal."""
    print(f"Query tokens : {tokens}\n")
    print(f"{'#':<3} {'Score':<8} {'Quartile':<10} {'Title'}")
    print("-" * 80)
    for i, row in results.iterrows():
        print(f"{i+1:<3} {row['bm25_score']:<8} {row['Quartile']:<10} {row['Title']}")
        print(f"    Areas: {row['Areas']}  |  H-index: {row['H_index']}  |  OA: {row['Open_Access']}")
        print()


def main():
    print("\n=== STEP 3: Query Processing ===\n")

    index, df = load_resources()

    # ── Test abstracts ─────────────────────────────────────────────────────
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
        print(f"\n{'='*80}")
        print(f"ABSTRACT: {abstract['label']}")
        print(f"{'='*80}\n")
        results = search(abstract["text"], index, df, top_n=5)
        tokens  = tokenize(abstract["text"])
        display_results(results, tokens)

    print("\n✓ Step 3 complete. Run step4_risk_assessment.py next.\n")


if __name__ == "__main__":
    main()
