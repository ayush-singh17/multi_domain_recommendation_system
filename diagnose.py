"""
diagnose.py — which part of the scoring finds (or misses) the right journals?

Put your abstract in abstract.txt, then run (from the project root):

    python diagnose.py                 # Q1 journals only (default)
    python diagnose.py --quartile Q2   # only Q2   (Q1 / Q2 / Q3 / Q4)
    python diagnose.py --quartile all  # everything
    python diagnose.py --top 25        # longer lists
    python diagnose.py --adapter       # query with SPECTER2 + adapter (if your embeddings were built that way)
    python diagnose.py --focus clinical    # apply a focus mode (affects the APP FINAL table)
    python diagnose.py --focus all         # compare the app's ranking under every focus mode

Shows ONLY journals of the chosen quartile:
  (1) top journals by embeddings alone   (2) top journals by BM25 alone
  (3) top journals by HYBRID score (embeddings + BM25 combined exactly as the app does it)
  (4) rank of your expected journals under all three: overall AND among that quartile only
  (5) where they land in the APP'S FINAL list (what the results page shows), vs relevance-only order

Expected journals: edit EXPECTED below, or put one exact title per line in expected.txt
(matching ignores capital letters).
"""
import argparse
import os
import pickle

import numpy as np
import pandas as pd

# same BM25, tokenizer and hybrid settings as the app, so the numbers here match the app
from step3b_bert_rerank import bm25_search, tokenize, ALPHA, BM25_CANDIDATES

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
    EXPECTED = [l.strip() for l in open("expected.txt", encoding="utf-8") if l.strip()]

ap = argparse.ArgumentParser()
ap.add_argument("--quartile", default="Q1", help="Q1, Q2, Q3, Q4 or all")
ap.add_argument("--top", type=int, default=15)
ap.add_argument("--focus", default="General / Best Fit",
                help='Focus mode used by the app: "General / Best Fit" (default), "Ethics / Philosophy", '
                     '"Clinical Impact", "Legal / Policy", "Technical / Engineering" — or "all" to compare every mode. '
                     'Partial names work (e.g. --focus clinical).')
ap.add_argument("--adapter", action="store_true",
                help="query with SPECTER2 + adapter (use when journal_embeddings.npy was built with --adapter)")
ap.add_argument("--dummy", action="store_true", help="plumbing test only (no model download)")
a = ap.parse_args()

abstract = open("abstract.txt", encoding="utf-8").read().strip()
df = pd.read_csv("journals_clean.csv", low_memory=False)
emb = np.load("journal_embeddings.npy")
bm25_index = pickle.load(open("bm25_index.pkl", "rb"))

if a.dummy:
    import re
    v = np.zeros(emb.shape[1], dtype=np.float32)
    for w in re.findall(r"[a-z]+", abstract.lower()):
        v[hash(w) % emb.shape[1]] += 1
    q = v / (np.linalg.norm(v) + 1e-9)
else:
    from encoder import load_encoder        # same loader the app uses
    model = load_encoder("allenai/specter2_base", adapter=a.adapter)
    q = model.encode([abstract], convert_to_numpy=True, normalize_embeddings=True)[0]

quart = df["SJR Best Quartile"].astype(str).values
is_all = a.quartile.lower() == "all"
keep = np.ones(len(df), dtype=bool) if is_all else (quart == a.quartile.upper())
label = "all quartiles" if is_all else a.quartile.upper()
print((f"Showing all journals: {len(df):,}" if is_all else f"Showing only {label} journals: {int(keep.sum()):,} of {len(df):,}") + "\n")


def ranks(order):
    """order = journal ids best-first  ->  (overall rank map, rank map among kept journals)"""
    overall = {int(i): r + 1 for r, i in enumerate(order)}
    kept = [int(i) for i in order if keep[int(i)]]
    return overall, {i: r + 1 for r, i in enumerate(kept)}, kept


# 1) embeddings alone
bert = emb @ q
bert_all, bert_q, bert_kept = ranks(np.argsort(-bert))

# 2) BM25 alone
bm_list = bm25_search(abstract, bm25_index, top_n=len(df))
bm_all, bm_q, bm_kept = ranks([d for d, _ in bm_list])
bm_score = dict(bm_list)

# 3) HYBRID — identical to hybrid_search() in step3b:
#    BERT min-max over the whole corpus; BM25 min-max over its top BM25_CANDIDATES only (others get 0)
bert_norm = (bert - bert.min()) / (bert.max() - bert.min() + 1e-9)
cand = bm_list[:BM25_CANDIDATES]
vals = np.array([s for _, s in cand], dtype=float)
bm_norm = np.zeros(len(df))
if len(vals):
    for d, s in cand:
        bm_norm[d] = (s - vals.min()) / (vals.max() - vals.min() + 1e-9)
hybrid = (1 - ALPHA) * bm_norm + ALPHA * bert_norm
hyb_all, hyb_q, hyb_kept = ranks(np.argsort(-hybrid))

print("BM25 uses only these words:", sorted(set(tokenize(abstract)))[:25], "\n")
print(f"TOP {a.top} {label} — embeddings alone")
for i in bert_kept[:a.top]:
    print(f"  {bert[i]:.3f}  [{quart[i]}]  {df.at[i, 'Title']}")
print(f"\nTOP {a.top} {label} — BM25 alone")
for d in bm_kept[:a.top]:
    print(f"  {bm_score[d]:6.2f}  [{quart[d]}]  {df.at[d, 'Title']}")
print(f"\nTOP {a.top} {label} — HYBRID (embeddings {ALPHA:.0%} + BM25 {1 - ALPHA:.0%}, as the app scores it)")
for i in hyb_kept[:a.top]:
    print(f"  {hybrid[i]:.3f}  [{quart[i]}]  {df.at[i, 'Title']}")

# ── 4) The app's own FINAL ranking (focus-aware): exactly what the results page is built from ──
from step6_strategy import build_strategy
try:
    from step5c_focus_filter import FOCUS_OPTIONS
except Exception:
    FOCUS_OPTIONS = ["General / Best Fit"]


def resolve_focus(name):
    if name.strip().lower() == "all":
        return list(FOCUS_OPTIONS)
    exact = [f for f in FOCUS_OPTIONS if f.lower() == name.strip().lower()]
    part = [f for f in FOCUS_OPTIONS if name.strip().lower() in f.lower()]
    hit = exact or (part if len(part) == 1 else [])
    if not hit:
        raise SystemExit(f"Unknown focus '{name}'. Use one of: " + ", ".join(f'"{f}"' for f in FOCUS_OPTIONS) + ', or "all".')
    return hit


class _QueryEncoder:                      # lets the app pipeline reuse the query vector computed above
    def encode(self, texts, **kwargs):
        return np.asarray([q])


def run_app(focus):
    """Run the app's real pipeline for one focus mode and compute the rank tables."""
    strategy = build_strategy(abstract, df, bm25_index, emb, _QueryEncoder(), focus=focus)
    app = strategy["ranked"].reset_index(drop=True)                           # sorted by final_score
    shown = app[app["risk_level"] != "High"].reset_index(drop=True)           # High-risk journals are hidden
    final_all, final_q, _ = ranks(shown["doc_id"].astype(int).tolist())
    rel_all, rel_q, _ = ranks(shown.sort_values("hybrid_norm", ascending=False)["doc_id"].astype(int).tolist())
    return {
        "focus": focus, "app": app, "shown": shown,
        "final_all": final_all, "final_q": final_q, "rel_all": rel_all, "rel_q": rel_q,
        "returned": set(app["doc_id"].astype(int)),
        "hidden": set(app.loc[app["risk_level"] == "High", "doc_id"].astype(int)),
        "focus_label": dict(zip(app["doc_id"].astype(int), app["focus_label"])) if "focus_label" in app else {},
    }


focuses = resolve_focus(a.focus)
runs = []
for _f in focuses:
    print(f"Running the app's own pipeline (build_strategy) with focus: {_f} ...")
    runs.append(run_app(_f))
print()

N_ALL, N_Q = len(df), int(keep.sum())
col = "same" if is_all else f"{label}-only"
print(f"\nWHERE YOUR EXPECTED JOURNALS RANK (1 = best)")
print(f"  'overall' = out of {N_ALL:,} journals" + ("" if is_all else f";  '{col}' = out of {N_Q:,} {label} journals"))
print(f"  {'journal':38} {'Q':>3} | {'EMBEDDINGS':^21} | {'BM25':^21} | {'HYBRID':^21}")
print(f"  {'':38} {'':>3} | {'overall':>9} {col:>11} | {'overall':>9} {col:>11} | {'overall':>9} {col:>11}")
some_skipped = False
for t in EXPECTED:
    m = df.index[df.Title.str.strip().str.lower() == t.strip().lower()]
    if len(m) == 0:
        print(f"  {t[:38]:38} not in dataset (check the exact title)")
        continue
    i = int(m[0])
    some_skipped |= not keep[i]
    cell = lambda d: str(d[i]) if keep[i] and i in d else "-"
    print(f"  {t[:38]:38} {quart[i]:>3} | {bert_all[i]:>9} {cell(bert_q):>11} | "
          f"{bm_all.get(i, '-'):>9} {cell(bm_q):>11} | {hyb_all[i]:>9} {cell(hyb_q):>11}")
if some_skipped:
    print(f"\n  ('-' in a {label}-only column = that journal is not {label}, so it has no {label}-only rank)")


# ── App ranking table(s) ─────────────────────────────────────────────────────────────────
def status_of(R, i):
    if i in R["hidden"]:
        return "hidden: High risk"
    return "shown" if i in R["returned"] else "not returned"


found = []
for t in EXPECTED:
    m = df.index[df.Title.str.strip().str.lower() == t.strip().lower()]
    if len(m):
        found.append((t, int(m[0])))

if len(runs) == 1:
    R = runs[0]
    print(f"\nWHAT THE RESULTS PAGE ACTUALLY SHOWS — focus: {R['focus']}  (1 = first result)")
    print(f"  FINAL = the app's final_score order (relevance + risk + SJR + speed + domain, with the focus nudge).")
    print(f"  RELEVANCE-ONLY = the same list re-ordered by relevance alone. If FINAL is much worse than")
    print(f"  RELEVANCE-ONLY for a journal, prestige/risk scoring is pushing it down.")
    print(f"  Focus nudge: Boosted x1.2 / Neutral x1.0 / Penalized x0.8 on the journal's relevance, by its subject area.")
    print(f"  List size: {len(R['shown']):,} overall" + ("" if is_all else f", {sum(1 for i in R['shown']['doc_id'] if keep[int(i)]):,} {label}"))
    print(f"  {'journal':38} {'Q':>3} | {'status':18} | {'focus':9} | {'FINAL':^21} | {'RELEVANCE-ONLY':^21}")
    print(f"  {'':38} {'':>3} | {'':18} | {'':9} | {'overall':>9} {col:>11} | {'overall':>9} {col:>11}")
    for t, i in found:
        status = status_of(R, i)
        ok = status == "shown"
        c2 = lambda d: str(d[i]) if (ok and keep[i] and i in d) else "-"
        fl = R["focus_label"].get(i, "-") if ok else "-"
        fa = str(R["final_all"][i]) if ok else "-"
        ra = str(R["rel_all"][i]) if ok else "-"
        print(f"  {t[:38]:38} {quart[i]:>3} | {status:18} | {fl:9} | {fa:>9} {c2(R['final_q']):>11} | {ra:>9} {c2(R['rel_q']):>11}")
    print("\n  'not returned' = outside the candidate pool or removed by the relevance gate.")
else:
    names = [f.split("/")[0].split()[0] for f in focuses]
    print(f"\nAPP FINAL RANK UNDER EACH FOCUS MODE   (cell = overall/{col}; 1 = first result)")
    print("  hidden = High risk (not shown)   n/r = not returned by the app   - = not in the chosen quartile")
    print(f"  {'journal':38} {'Q':>3} | " + " ".join(f"{n:>13}" for n in names))
    for t, i in found:
        cells = []
        for R in runs:
            st = status_of(R, i)
            if st == "shown":
                qcell = str(R["final_q"][i]) if (keep[i] and i in R["final_q"]) else "-"
                cells.append(f"{R['final_all'][i]}/{qcell}")
            else:
                cells.append("hidden" if st.startswith("hidden") else "n/r")
        print(f"  {t[:38]:38} {quart[i]:>3} | " + " ".join(f"{c:>13}" for c in cells))
    print("\n  List sizes: " + ", ".join(f"{n}: {len(R['shown']):,}" for n, R in zip(names, runs)))
