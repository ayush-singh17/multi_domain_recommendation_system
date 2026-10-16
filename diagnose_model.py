"""
diagnose_model.py — does a different encoder rank the journals you EXPECT higher?

Cheap version of diagnose.py: instead of re-embedding all 29,553 journals with a new
model, it re-embeds only a candidate pool (~3,500 journals) and compares ranks inside it:
    pool = top-3000 by your CURRENT embeddings + top-500 by BM25 + the EXPECTED journals.
Both the current model and the new one rank this same pool, so the comparison is fair
(it measures re-ranking power, not recall outside the pool).

    python diagnose_model.py --model sentence-transformers/all-mpnet-base-v2
    python diagnose_model.py --model BAAI/bge-base-en-v1.5

Needs abstract.txt in the project root. Takes a few minutes (embeds ~3.5k journal texts).
Texts come from bert_texts.pkl (your enriched journal_text_v2), row-aligned with the CSV.
"""
import argparse
import pickle
import re

import numpy as np
import pandas as pd

try:
    from step3b_bert_rerank import bm25_search
except Exception:                      # only used by the offline plumbing test
    bm25_search = None

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


import os as _os
if _os.path.exists("expected.txt"):      # optional: one exact journal title per line
    EXPECTED = [l.strip() for l in open("expected.txt", encoding="utf-8") if l.strip()]

class Dummy:
    def __init__(self, dim=512):
        self.dim = dim

    def encode(self, texts, **kw):
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in re.findall(r"[a-z]+", t.lower()):
                out[i, hash(w) % self.dim] += 1
        return out / (np.linalg.norm(out, axis=1, keepdims=True) + 1e-9)


def load(name, dummy):
    if dummy:
        return Dummy(768 if "specter2" in name else 512)
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name)


def enc(m, texts):
    return m.encode(texts, convert_to_numpy=True, normalize_embeddings=True,
                    batch_size=32, show_progress_bar=len(texts) > 100)


ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--dummy", action="store_true")
ap.add_argument("--strip-name", action="store_true", help="remove the journal name from the profile text before embedding")
ap.add_argument("--pool-embed", type=int, default=3000)
ap.add_argument("--pool-bm25", type=int, default=500)
a = ap.parse_args()

abstract = open("abstract.txt", encoding="utf-8").read().strip()
df = pd.read_csv("journals_clean.csv", low_memory=False)
texts = pickle.load(open("bert_texts.pkl", "rb"))
emb = np.load("journal_embeddings.npy")

# current model ranking over everything -> candidate pool
cur_model = load("allenai/specter2_base", a.dummy)
q_cur = enc(cur_model, [abstract])[0]
cur = emb @ q_cur
pool = set(np.argsort(-cur)[: a.pool_embed].tolist())
if bm25_search is not None:
    pool |= {d for d, _ in bm25_search(abstract, pickle.load(open("bm25_index.pkl", "rb")), a.pool_bm25)}
_low = df.Title.str.strip().str.lower()
exp_idx = {t: int(df.index[_low == t.strip().lower()][0]) for t in EXPECTED if (_low == t.strip().lower()).any()}
for t in EXPECTED:
    if t not in exp_idx:
        print("  (not found in dataset, check spelling):", t)
pool |= set(exp_idx.values())
pool = sorted(pool)
print(f"Candidate pool: {len(pool)} journals")

# new model over the pool
new_model = load(a.model, a.dummy)
q_new = enc(new_model, [abstract])[0]
def strip_name(i, t):
    name = str(df.at[i, "Title"]).lower()
    return t[len(name):].lstrip(" .,") if t.lower().startswith(name) else t

pool_texts = [strip_name(i, texts[i]) if a.strip_name else texts[i] for i in pool]
if a.strip_name:
    print("Example profile text WITHOUT the journal name:", pool_texts[0][:160], "...")
d_new = enc(new_model, pool_texts)
s_new = d_new @ q_new
s_cur = cur[pool]

def ranks(scores):
    order = np.argsort(-scores)
    r = np.empty(len(pool), dtype=int); r[order] = np.arange(1, len(pool) + 1)
    return r, order

r_cur, o_cur = ranks(s_cur)
r_new, o_new = ranks(s_new)
pos = {j: k for k, j in enumerate(pool)}

print(f"\nTOP 15 with {a.model}" + (" (journal names removed)" if a.strip_name else ""))
for k in o_new[:15]:
    print(f"  {s_new[k]:.3f}  {df.at[pool[k], 'Title']}")
print(f"\nRANK OF EXPECTED JOURNALS within the same {len(pool)}-journal pool (1 = best)")
print(f"  {'journal':58} {'current':>8} {'new':>6}")
for t, i in exp_idx.items():
    print(f"  {t[:58]:58} {r_cur[pos[i]]:>8} {r_new[pos[i]]:>6}")
print(f"\nMedian rank of expected: current {np.median([r_cur[pos[i]] for i in exp_idx.values()]):.0f}"
      f" -> new {np.median([r_new[pos[i]] for i in exp_idx.values()]):.0f}")
