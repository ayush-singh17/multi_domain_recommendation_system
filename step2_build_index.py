"""
STEP 2 — Build BM25 Index (Offline)
Journal Recommendation System

What this script does:
  - Loads journals_clean.csv
  - Tokenizes the journal_text field
  - Builds a BM25 index (from scratch, no extra libraries needed)
  - Saves bm25_index.pkl  ← used by the app at search time

Run this ONCE. After this, the app never touches the raw dataset again.
"""

import pandas as pd
import pickle
import re
import math
from collections import defaultdict


# ── Config ────────────────────────────────────────────────────────────────────
INPUT_FILE  = "journals_clean.csv"
INDEX_FILE  = "bm25_index.pkl"

# BM25 tuning parameters (standard values, no need to change)
K1 = 1.5   # term frequency saturation
B  = 0.75  # length normalisation
# ─────────────────────────────────────────────────────────────────────────────


def tokenize(text: str) -> list[str]:
    """Lowercase and extract alphabetic tokens only."""
    return re.findall(r"[a-z]+", str(text).lower())


def build_bm25_index(corpus: list[str]) -> dict:
    """
    Builds a BM25 index from a list of document strings.

    Returns a dict with everything needed to score queries at runtime:
      - inverted_index : {term -> [(doc_id, term_freq), ...]}
      - doc_lengths    : [len(doc_tokens), ...]
      - avgdl          : average document length
      - N              : total number of documents
    """
    print(f"  Tokenizing {len(corpus):,} documents ...")
    tokenized_corpus = [tokenize(doc) for doc in corpus]

    doc_lengths = [len(doc) for doc in tokenized_corpus]
    avgdl = sum(doc_lengths) / len(doc_lengths)
    N = len(tokenized_corpus)

    print(f"  Building inverted index ...")
    inverted_index = defaultdict(list)

    for doc_id, tokens in enumerate(tokenized_corpus):
        term_freq = defaultdict(int)
        for token in tokens:
            term_freq[token] += 1
        for term, freq in term_freq.items():
            inverted_index[term].append((doc_id, freq))

    print(f"  Vocabulary size: {len(inverted_index):,} unique terms")
    print(f"  Average document length: {avgdl:.2f} tokens")

    return {
        "inverted_index": dict(inverted_index),
        "doc_lengths":    doc_lengths,
        "avgdl":          avgdl,
        "N":              N,
    }


def score_query(query: str, index: dict, top_n: int = 20) -> list[tuple[int, float]]:
    """
    Scores all documents against a query using BM25 Okapi formula.
    Returns top_n (doc_id, score) pairs sorted by descending score.

    This function is defined here so it can be imported and used by the app.
    """
    tokens = tokenize(query)
    inverted = index["inverted_index"]
    doc_lengths = index["doc_lengths"]
    avgdl = index["avgdl"]
    N = index["N"]

    scores = defaultdict(float)

    for term in tokens:
        if term not in inverted:
            continue

        posting_list = inverted[term]
        df_t = len(posting_list)  # number of docs containing this term

        # BM25 IDF (Robertson-Sparck Jones)
        idf = math.log((N - df_t + 0.5) / (df_t + 0.5) + 1)

        for doc_id, freq in posting_list:
            dl = doc_lengths[doc_id]
            # BM25 TF with length normalisation
            tf = (freq * (K1 + 1)) / (freq + K1 * (1 - B + B * dl / avgdl))
            scores[doc_id] += idf * tf

    return sorted(scores.items(), key=lambda x: -x[1])[:top_n]


def verify_index(index: dict, df: pd.DataFrame):
    """Quick smoke test to confirm the index returns sensible results."""
    print("\n  Smoke test — query: 'machine learning neural network'")
    results = score_query("machine learning neural network", index, top_n=3)
    for doc_id, score in results:
        title = df.iloc[doc_id]["Title"]
        print(f"    [{score:.3f}]  {title}")

    print("\n  Smoke test — query: 'cardiology heart disease clinical trials'")
    results = score_query("cardiology heart disease clinical trials", index, top_n=3)
    for doc_id, score in results:
        title = df.iloc[doc_id]["Title"]
        print(f"    [{score:.3f}]  {title}")


def main():
    print("\n=== STEP 2: Build BM25 Index ===\n")

    # Load cleaned dataset
    print(f"[1/3] Loading {INPUT_FILE} ...")
    df = pd.read_csv(INPUT_FILE)
    print(f"      {len(df):,} journals loaded")

    # Build index
    print("\n[2/3] Building BM25 index ...")
    corpus = df["journal_text"].tolist()
    index = build_bm25_index(corpus)

    # Save index
    print(f"\n[3/3] Saving index to {INDEX_FILE} ...")
    with open(INDEX_FILE, "wb") as f:
        pickle.dump(index, f)
    print(f"      Saved successfully.")

    # Verify
    verify_index(index, df)

    print("\n✓ Step 2 complete. Run step3_query.py next.\n")


if __name__ == "__main__":
    main()
