"""Diagnose embedding, BM25, hybrid, and app focus-mode final ranks.

Place this file in the project root alongside abstract.txt and the model assets.
Run: python diagnose_focus.py --focus "Clinical Impact"
     python diagnose_focus.py --all-focus --candidates 30

The focus rankings are among the app's hybrid candidate pool, not all 29,553
journals. Change --candidates to match build_strategy's top_n if needed.
"""

import argparse
import os
import pickle

import numpy as np
import pandas as pd

from step3b_bert_rerank import ALPHA, BM25_CANDIDATES, bm25_search, tokenize
from step5c_focus_filter import FOCUS_CONFIG, get_focus_multiplier

FOCUS_OPTIONS = [
    "General / Best Fit",
    "Ethics / Philosophy",
    "Clinical Impact",
    "Legal / Policy",
    "Technical / Engineering",
    "Cross-disciplinary Science",
]

EXPECTED = [
    "IEEE Transactions on Industrial Informatics",
    "IEEE Transactions on Information Forensics and Security",
    "IEEE Transactions on Network and Service Management",
    "Computers and Security",
    "Journal of Network and Computer Applications",
    "Future Generation Computer Systems",
    "Computer Networks",
    "IEEE Internet of Things Journal",
]
if os.path.exists("expected.txt"):
    with open("expected.txt", encoding="utf-8") as f:
        EXPECTED = [line.strip() for line in f if line.strip()]

parser = argparse.ArgumentParser()
parser.add_argument("--quartile", default="Q1", choices=["Q1", "Q2", "Q3", "Q4", "all"])
parser.add_argument("--top", type=int, default=15)
parser.add_argument("--dummy", action="store_true", help="plumbing test only (no model download)")
parser.add_argument("--focus", choices=FOCUS_OPTIONS, default=FOCUS_OPTIONS[0],
                    help="Focus Mode selected in the app")
parser.add_argument("--all-focus", action="store_true", help="compare all six Focus Modes")
parser.add_argument("--candidates", type=int, default=30,
                    help="hybrid candidate pool size used by build_strategy (default: 30)")
args = parser.parse_args()
if args.top < 1 or args.candidates < 1:
    parser.error("--top and --candidates must be positive")

with open("abstract.txt", encoding="utf-8") as f:
    abstract = f.read().strip()
if not abstract:
    parser.error("abstract.txt must contain an abstract")

df = pd.read_csv("journals_clean.csv", low_memory=False)
emb = np.load("journal_embeddings.npy")
with open("bm25_index.pkl", "rb") as f:
    bm25_index = pickle.load(f)
if len(df) != len(emb) or len(df) != bm25_index["N"]:
    parser.error("CSV, embeddings and BM25 index row counts differ; rebuild the assets")

if args.dummy:
    import re

    vector = np.zeros(emb.shape[1], dtype=np.float32)
    for word in re.findall(r"[a-z]+", abstract.lower()):
        vector[hash(word) % emb.shape[1]] += 1
    query = vector / (np.linalg.norm(vector) + 1e-9)
else:
    from sentence_transformers import SentenceTransformer
    from step3b_bert_rerank import MODEL_NAME

    model = SentenceTransformer(MODEL_NAME)
    query = model.encode([abstract], convert_to_numpy=True,
                         normalize_embeddings=True)[0]

quart = df["SJR Best Quartile"].astype(str).to_numpy()
keep = np.ones(len(df), dtype=bool) if args.quartile == "all" else quart == args.quartile
label = "all quartiles" if args.quartile == "all" else args.quartile
print(f"Showing {label}: {int(keep.sum()):,} of {len(df):,} journals\n")

# Embeddings: cosine scores against every journal.
bert = emb @ query
bert_order_all = np.argsort(-bert, kind="stable").tolist()
bert_rank_all = {int(i): rank for rank, i in enumerate(bert_order_all, 1)}
bert_order = [int(i) for i in bert_order_all if keep[i]]
bert_rank = {i: rank for rank, i in enumerate(bert_order, 1)}

# BM25: the full nonzero-score ranking for diagnosis. The live hybrid uses
# only the top BM25_CANDIDATES as a sparse-score bonus.
bm_all = bm25_search(abstract, bm25_index, top_n=len(df))
bm_rank_all = {int(i): rank for rank, (i, _) in enumerate(bm_all, 1)}
bm = [(int(i), score) for i, score in bm_all if keep[i]]
bm_rank = {i: rank for rank, (i, _) in enumerate(bm, 1)}

# Exactly the hybrid normalization in step3b_bert_rerank.hybrid_search:
# normalize dense scores over the full corpus and sparse scores only among
# the top BM25_CANDIDATES; missing sparse scores contribute zero.
bert_norm = (bert - bert.min()) / (bert.max() - bert.min() + 1e-9)
hybrid = ALPHA * bert_norm
bm_candidates = bm_all[:BM25_CANDIDATES]
if bm_candidates:
    bm_values = np.asarray([score for _, score in bm_candidates], dtype=float)
    bm_min, bm_max = bm_values.min(), bm_values.max()
    for doc_id, score in bm_candidates:
        sparse_norm = (score - bm_min) / (bm_max - bm_min + 1e-9)
        hybrid[doc_id] += (1 - ALPHA) * sparse_norm
hybrid_order_all = np.argsort(-hybrid, kind="stable").tolist()
hybrid_rank_all = {int(i): rank for rank, i in enumerate(hybrid_order_all, 1)}
hybrid_order = [int(i) for i in hybrid_order_all if keep[i]]
hybrid_rank = {i: rank for rank, i in enumerate(hybrid_order, 1)}

print("BM25 uses only these words:", sorted(set(tokenize(abstract)))[:25], "\n")
for heading, order, scores in [
    ("embeddings", bert_order, bert),
    ("BM25", [i for i, _ in bm], dict(bm)),
    (f"hybrid (ALPHA={ALPHA:g})", hybrid_order, hybrid),
]:
    print(f"TOP {args.top} {label} — {heading}")
    for i in order[:args.top]:
        print(f"  {scores[i]:7.3f}  [{quart[i]}]  {df.at[i, 'Title']}")
    print()

n_all, n_q = len(df), int(keep.sum())
column = "same" if args.quartile == "all" else f"{args.quartile}-only"
print("WHERE YOUR EXPECTED JOURNALS RANK (1 = best)")
print(f"  overall = out of {n_all:,}" +
      ("" if column == "same" else f"; {column} = out of {n_q:,}"))
print(f"  {'journal':46} {'Q':>3} | {'EMBEDDINGS':^21} | {'BM25':^21} | {'HYBRID':^21}")
print(f"  {'':46} {'':>3} | {'overall':>9} {column:>11} | "
      f"{'overall':>9} {column:>11} | {'overall':>9} {column:>11}")

titles = df["Title"].fillna("").str.strip().str.casefold()
for title in EXPECTED:
    matches = df.index[titles == title.strip().casefold()]
    if len(matches) == 0:
        print(f"  {title[:46]:46} not in dataset (check the exact title)")
        continue
    i = int(matches[0])
    def quart_rank(ranks):
        return str(ranks.get(i, "-")) if keep[i] else "-"
    print(f"  {title[:46]:46} {quart[i]:>3} | "
          f"{bert_rank_all[i]:>9} {quart_rank(bert_rank):>11} | "
          f"{str(bm_rank_all.get(i, '-')):>9} {quart_rank(bm_rank):>11} | "
          f"{hybrid_rank_all[i]:>9} {quart_rank(hybrid_rank):>11}")

print("\nHybrid rank is before risk scoring, relevance filtering, and plan selection.")

selected = FOCUS_OPTIONS if args.all_focus else [args.focus]
areas = df["Areas"].fillna("").tolist()

# Full-corpus what-if shows whether a focus can improve an expected journal's
# rank in principle. The live app does not apply focus until AFTER shortlisting.
for focus in selected:
    multipliers = np.asarray([get_focus_multiplier(area, focus)[0]
                              for area in areas], dtype=float)
    adjusted = np.round(np.round(hybrid, 4) * multipliers, 4)
    order = np.argsort(-adjusted, kind="stable").tolist()
    overall_ranks = {int(i): pos for pos, i in enumerate(order, 1)}
    visible_ids = [int(i) for i in order if keep[i]]
    quartile_ranks = {i: pos for pos, i in enumerate(visible_ids, 1)}

    print(f"\nFOCUS: {focus} — full-corpus adjusted hybrid (WHAT-IF ONLY)")
    if focus not in FOCUS_CONFIG and focus != "General / Best Fit":
        print("  No focus rule exists for this mode in step5c_focus_filter.py; "
              "it currently behaves like General / Best Fit.")
    print(f"TOP {args.top} {label} — focus-adjusted hybrid")
    for i in visible_ids[:args.top]:
        print(f"  {adjusted[i]:7.4f}  [{quart[i]}]  {df.at[i, 'Title']}")
    print("EXPECTED JOURNALS — adjusted-hybrid rank (overall / " +
          ("same" if args.quartile == "all" else f"{args.quartile}-only") + ")")
    for title in EXPECTED:
        matches = df.index[titles == title.strip().casefold()]
        if len(matches) == 0:
            print(f"  {title[:46]:46}  not in dataset")
            continue
        i = int(matches[0])
        print(f"  {title[:46]:46}  {overall_ranks[i]:>5} / "
              f"{str(quartile_ranks.get(i, '-')):>5}")

# App final rankings use the hybrid shortlist, risk, and the relevance gate.
if args.dummy:
    print("\nApp final ranking skipped in --dummy mode (the app model is needed).")
else:
    from step3b_bert_rerank import hybrid_search
    from step4_risk_assessment import assess_risk
    from step5_ranking import rank

    candidate_count = min(args.candidates, len(df))
    candidates = hybrid_search(abstract, bm25_index, emb, model, df,
                               top_n=candidate_count)
    assessed = assess_risk(candidates, abstract)
    for focus in selected:
        ranked = rank(assessed, focus=focus, abstract=abstract)
        visible = ranked if args.quartile == "all" else ranked[ranked["Quartile"] == args.quartile]
        overall_ranks = {int(row["doc_id"]): pos for pos, (_, row) in enumerate(ranked.iterrows(), 1)}
        quartile_ranks = {int(row["doc_id"]): pos for pos, (_, row) in enumerate(visible.iterrows(), 1)}

        print(f"\nFOCUS: {focus} — final app ranking from {candidate_count} hybrid candidates")
        if focus not in FOCUS_CONFIG and focus != "General / Best Fit":
            print("  Note: no focus rule exists for this mode in step5c_focus_filter.py; "
                  "its ranking currently matches General / Best Fit.")
        print(f"TOP {args.top} {label} — final score")
        for _, row in visible.head(args.top).iterrows():
            print(f"  {row['final_score']:7.4f}  [{row['Quartile']}]  {row['Title']}")

        print("EXPECTED JOURNALS — app final rank (overall / " +
              ("same" if args.quartile == "all" else f"{args.quartile}-only") + ")")
        for title in EXPECTED:
            matches = df.index[titles == title.strip().casefold()]
            if len(matches) == 0:
                print(f"  {title[:46]:46}  not in dataset")
                continue
            doc_id = int(matches[0])
            overall = overall_ranks.get(doc_id, "-")
            q_rank = quartile_ranks.get(doc_id, "-")
            print(f"  {title[:46]:46}  {str(overall):>5} / {str(q_rank):>5}")
        print("  '-' means absent from the hybrid shortlist, removed by the app's "
              "relevance gate, or outside the chosen quartile.")
