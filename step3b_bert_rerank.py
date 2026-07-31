"""
STEP 3b — BERT Reranker
Journal Recommendation System

What this script does:
  - Loads precomputed journal embeddings (journal_embeddings.npy)
  - At runtime: encodes ONLY the abstract (< 1 second)
  - Computes cosine similarity between abstract and all 29,553 journals
  - Combines BM25 score + BERT score into a hybrid score
  - Returns reranked candidates for the risk + ranking pipeline

Hybrid formula:
  hybrid_score = (1 - ALPHA) × bm25_norm + ALPHA × bert_score
  ALPHA = 0.8  → BERT gets 80% weight, BM25 gets 20%

Why 60/40 in favour of BERT?
  - BERT understands synonyms and meaning  ("cardiac" = "heart")
  - BM25 catches exact keyword matches that BERT sometimes misses
  - 60/40 tested to give best balance for scientific text
"""

import numpy as np
import pickle
import math
import re
import time
from collections import defaultdict


# ── Config ────────────────────────────────────────────────────────────────────
EMBEDDINGS_FILE = "journal_embeddings.npy"
TEXTS_FILE      = "bert_texts.pkl"
MODEL_NAME      = "allenai/specter2_base"
ALPHA           = 0.8    # BERT weight  (1-ALPHA = BM25 weight)
BM25_CANDIDATES = 100    # BM25 retrieves this many; BERT reranks them
FINAL_TOP_N     = 20     # final candidates passed to risk + ranking
# ─────────────────────────────────────────────────────────────────────────────


# ── Load resources ────────────────────────────────────────────────────────────

def load_bert_resources():
    """Load precomputed embeddings and BERT model. Cached by caller."""
    print("  Loading journal embeddings...")
    embeddings = np.load(EMBEDDINGS_FILE)          # shape: (29553, 768)
    print(f"  Embeddings shape: {embeddings.shape}")

    with open(TEXTS_FILE, "rb") as f:
        texts = pickle.load(f)

    print(f"  Loading BERT model: {MODEL_NAME}")
    from sentence_transformers import SentenceTransformer
    import torch
    model = SentenceTransformer(MODEL_NAME)
    if torch.cuda.is_available():
        model = model.to(torch.device("cuda"))
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("  Using CPU")

    return embeddings, texts, model


# ── BM25 (copied from step2_build_index for self-contained use) ───────────────

K1 = 1.5
B  = 0.75

STOPWORDS = {
    # ── Standard English stopwords ────────────────────────────────────────
    "the","a","an","and","or","of","in","on","for","to","is","are","was",
    "were","be","been","being","have","has","had","do","does","did","will",
    "would","could","should","may","might","can","this","that","these",
    "those","we","our","their","its","it","as","by","with","from","at",
    "both","between","into","such","each","however","while","among","within",
    "across","through","after","about","over","under","new","two","three",
    "high","low","large","small","also","well","than","more","which",

    # ── Generic academic writing words (appear in every abstract) ─────────
    "using","used","use","based","paper","proposed","method","methods",
    "approach","results","show","shows","propose","present","achieve",
    "accuracy","dataset","existing","outperform","evaluate","evaluation",
    "experiment","experiments","train","training","test","testing","compare",
    "comparison","demonstrate","analysis","analyze","work","research","study",
    "task","tasks","problem","problems","feature","features","algorithm",
    "algorithms","layer","layers","image","images","benchmark","state","art",
    "level","levels","achieve","achieves","achieved","show","shown",
    "significant","significantly","improvement","improve","improved",

    # ── High-frequency niche words — low retrieval signal ─────────────────
    # These appear in almost every academic abstract and journal title,
    # so they match everything and tell BM25 nothing useful.
    "journal","journals","manuscript","manuscripts","article","articles",
    "publication","publications","publishing","published","publish",
    "review","reviews","letter","letters","report","reports","proceedings",
    "conference","international","national","annual","quarterly","weekly",
    "volume","issue","edition","series","bulletin","gazette","digest",
    "science","sciences","scientific","technology","technologies",
    "engineering","applied","theoretical","computational","advanced",
    "general","special","current","modern","contemporary","new",

    # ── Generic ML/AI words already covered above ─────────────────────────
    "model","models","system","systems","network","networks","learning",
    "performance","framework","prediction","predicting","predict",
    "classification","classifying","classify","detection","detecting",
    "data","feature","features","layer","layers","image","images",
}


def tokenize(text: str) -> list:
    tokens = re.findall(r"[a-z]+", str(text).lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 3]


def bm25_search(abstract: str, bm25_index: dict, top_n: int) -> list:
    """Returns [(doc_id, raw_bm25_score), ...] for top_n results."""
    tokens   = tokenize(abstract)
    inverted = bm25_index["inverted_index"]
    doc_lengths = bm25_index["doc_lengths"]
    avgdl    = bm25_index["avgdl"]
    N        = bm25_index["N"]
    scores   = defaultdict(float)

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

    return sorted(scores.items(), key=lambda x: -x[1])[:top_n]


# ── BERT encoding ─────────────────────────────────────────────────────────────

def encode_abstract(abstract: str, model) -> np.ndarray:
    """Encode the abstract into a 768-dim vector. Takes < 1 second."""
    emb = model.encode(
        [abstract],
        convert_to_numpy=True,
        normalize_embeddings=True,   # L2 norm → cosine sim = dot product
        show_progress_bar=False,
    )
    return emb[0]   # shape: (768,)


# ── Hybrid search ─────────────────────────────────────────────────────────────

def hybrid_search(
    abstract:    str,
    bm25_index:  dict,
    embeddings:  np.ndarray,
    model,
    df,
    top_n:       int = FINAL_TOP_N,
) -> "pd.DataFrame":
    """
    Full hybrid pipeline:
      1. BM25 retrieves BM25_CANDIDATES candidates (fast keyword match)
      2. BERT scores ALL 29,553 journals (fast dot product on precomputed embeddings)
      3. Scores are normalised and combined with ALPHA weighting
      4. Returns top_n as a DataFrame with all metadata + scores
    """
    import pandas as pd

    t0 = time.time()

    # ── Step 1: BM25 candidates ───────────────────────────────────────────
    bm25_results = bm25_search(abstract, bm25_index, top_n=BM25_CANDIDATES)
    bm25_doc_ids = [doc_id for doc_id, _ in bm25_results]
    bm25_scores  = {doc_id: score for doc_id, score in bm25_results}

    # ── Step 2: BERT similarity across ALL journals ───────────────────────
    abstract_emb  = encode_abstract(abstract, model)          # (768,)
    bert_scores   = embeddings @ abstract_emb                 # (29553,) dot products

    # ── Step 3: Normalise both score sets ─────────────────────────────────
    # BM25: normalise only within the candidate pool
    bm25_vals = np.array([bm25_scores[d] for d in bm25_doc_ids], dtype=float)
    bm25_min, bm25_max = bm25_vals.min(), bm25_vals.max()
    bm25_norm_map = {
        doc_id: (bm25_scores[doc_id] - bm25_min) / (bm25_max - bm25_min + 1e-9)
        for doc_id in bm25_doc_ids
    }

    # BERT: already normalised (cosine similarity in [−1, 1], typically [0.7, 0.95])
    # Shift to [0, 1] using min-max over full corpus
    bert_min  = bert_scores.min()
    bert_max  = bert_scores.max()
    bert_norm = (bert_scores - bert_min) / (bert_max - bert_min + 1e-9)

    # ── Step 4: Combine scores ────────────────────────────────────────────
    # Use BERT score for ALL 29,553 journals, add BM25 bonus for candidates
    combined = {}
    for doc_id in range(len(embeddings)):
        b_score = float(bert_norm[doc_id])
        k_score = bm25_norm_map.get(doc_id, 0.0)
        combined[doc_id] = (1 - ALPHA) * k_score + ALPHA * b_score

    # ── Step 5: Take top_n ────────────────────────────────────────────────
    top_results = sorted(combined.items(), key=lambda x: -x[1])[:top_n]

    # ── Step 6: Build result DataFrame ───────────────────────────────────
    rows = []
    for doc_id, hybrid_score in top_results:
        row = df.iloc[doc_id]
        rows.append({
            "doc_id":       doc_id,
            "hybrid_score": round(hybrid_score, 4),
            "bm25_score":   round(bm25_scores.get(doc_id, 0.0), 4),
            "bert_score":   round(float(bert_scores[doc_id]), 4),
            "Title":        row["Title"],
            "Publisher":    row["Publisher"],
            "SJR":          row["SJR"],
            "Quartile":     row["SJR Best Quartile"],
            "H_index":      row["H index"],
            "Citations":    row["Citations / Doc. (2years)"],
            "Open_Access":  row["Open Access"],
            "Country":      row["Country"],
            "Coverage":     row["Coverage"],
            "Categories":   row["Categories"],
            "Areas":        row["Areas"],
            "Issn":         row["Issn"],
            "apc_usd":      row.get("apc_usd",      None),
            "apc_currency": row.get("apc_currency",  None),
            "apc_amount":   row.get("apc_amount",    None),
            "apc_url":      row.get("apc_url",       None),
            "citescore":    row.get("citescore",     None),
            "impact_factor":row.get("impact_factor", None),
            "trend":            row.get("trend",            None),
            "weeks_to_publish":  row.get("weeks_to_publish",  None),
            "months_to_publish": row.get("months_to_publish", None),
            "in_doaj":           row.get("in_doaj",           False),
            "mahe_approved":     row.get("mahe_approved",     0),
        })

    elapsed = time.time() - t0
    print(f"  Hybrid search done in {elapsed:.2f}s")

    return pd.DataFrame(rows)


# ── Display ───────────────────────────────────────────────────────────────────

def display_hybrid_results(results: "pd.DataFrame"):
    print(f"\n{'#':<4} {'Hybrid':<8} {'BERT':<8} {'BM25':<8} {'Q':<5} {'H':<6} Title")
    print("-" * 90)
    for i, row in results.iterrows():
        print(
            f"{i+1:<4} {row['hybrid_score']:<8} {row['bert_score']:<8} "
            f"{row['bm25_score']:<8} {row['Quartile']:<5} "
            f"{int(row['H_index']):<6} {row['Title']}"
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import pickle, pandas as pd

    print("\n=== STEP 3b: BERT Hybrid Search ===\n")

    # Load BM25 index
    print("Loading BM25 index...")
    with open("bm25_index.pkl", "rb") as f:
        bm25_index = pickle.load(f)

    # Load dataset
    print("Loading dataset...")
    df = pd.read_csv("journals_clean.csv")

    # Load BERT resources
    print("Loading BERT resources...")
    embeddings, texts, model = load_bert_resources()

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
        print(f"\n{'='*90}")
        print(f"ABSTRACT: {abstract['label']}")
        print(f"{'='*90}")
        results = hybrid_search(abstract["text"], bm25_index, embeddings, model, df, top_n=10)
        display_hybrid_results(results)

    print("\n✓ Step 3b complete. Now update step5_ranking.py to use hybrid scores.\n")


if __name__ == "__main__":
    main()
