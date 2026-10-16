"""
eval_profiles.py — does the enriched journal text find the right journal better?

Uses the pilot cache (pilot_cache/*.json) and needs no new API calls.

For each pilot journal:
  - split its papers 80/20 (by a fixed shuffle)
  - build the journal profile from the 80% TRAIN papers only
  - use abstracts of the 20% HELD-OUT papers as search queries
  - ask: does the true journal rank in the top-k among all pilot journals?

Three journal texts are compared (same pool of journals, same queries):
  A  old          : journal_text from journals_clean.csv (title + categories + areas)
  B  enriched     : A + top topics + top keywords          (no paper titles)
  C  enriched+T   : B + a few recent titles

IMPORTANT: the candidate pool is only the pilot journals (~200), so absolute scores
are much higher than they would be over 29.5k journals. Only the DIFFERENCE between
A, B and C is meaningful.

Usage:
    python eval_profiles.py                              # allenai/specter2_base (what the app uses now)
    python eval_profiles.py --model sentence-transformers/allenai-specter
    python eval_profiles.py --model BAAI/bge-base-en-v1.5
    python eval_profiles.py --model sentence-transformers/all-mpnet-base-v2
    python eval_profiles.py --adapter                    # SPECTER2 + retrieval adapter (pip install adapters)
    python eval_profiles.py --dummy            # fast offline sanity check, not meaningful scores
"""

import argparse
import glob
import json
import os
import random
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openalex_pilot import build_profile, rebuild_abstract  # noqa: E402

CACHE = "pilot_cache"
CSV_IN = "journals_clean.csv"


# ── Embedders ────────────────────────────────────────────────────────────────
class DummyEmbedder:
    """Hashed bag-of-words — only to test the plumbing without downloading a model."""
    def encode(self, texts, **kw):
        out = np.zeros((len(texts), 512), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in re.findall(r"[a-z]+", t.lower()):
                out[i, hash(w) % 512] += 1.0
        n = np.linalg.norm(out, axis=1, keepdims=True) + 1e-9
        return out / n


class SpecterAdapterEmbedder:
    """SPECTER2 base + its retrieval ('proximity') adapter, CLS-token embedding.
    Needs:  pip install adapters
    UNTESTED here (no network in my sandbox) — check the allenai/specter2 model card if it errors."""
    def __init__(self):
        import torch
        from transformers import AutoTokenizer
        from adapters import AutoAdapterModel
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained("allenai/specter2_base")
        self.model = AutoAdapterModel.from_pretrained("allenai/specter2_base")
        name = self.model.load_adapter("allenai/specter2", source="hf", load_as="proximity", set_active=True)
        self.model.set_active_adapters(name)        # make sure it is really active (v1 run warned it was not)
        self.dev = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
        self.model.to(self.dev).eval()

    def encode(self, texts, batch_size=32, **kw):
        outs = []
        with self.torch.no_grad():
            for i in range(0, len(texts), batch_size):
                b = self.tok(texts[i:i + batch_size], padding=True, truncation=True, max_length=512,
                             return_tensors="pt", return_token_type_ids=False).to(self.dev)
                h = self.model(**b).last_hidden_state[:, 0, :]          # CLS token
                h = self.torch.nn.functional.normalize(h, dim=1)
                outs.append(h.cpu().numpy())
        return np.vstack(outs)


def load_model(args):
    if args.dummy:
        return DummyEmbedder()
    if args.adapter:
        return SpecterAdapterEmbedder()
    from sentence_transformers import SentenceTransformer
    import torch
    m = SentenceTransformer(args.model)
    if torch.cuda.is_available():
        m = m.to(torch.device("cuda"))
    elif torch.backends.mps.is_available():
        m = m.to(torch.device("mps"))
    return m


def embed(model, texts, kind, args, batch=32):
    """kind = 'query' or 'doc'. E5 models need 'query: ' / 'passage: ' prefixes."""
    if "e5" in args.model.lower() and not args.adapter:
        texts = [("query: " if kind == "query" else "passage: ") + t for t in texts]
    return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True,
                        batch_size=batch, show_progress_bar=False)


# ── Evaluation ───────────────────────────────────────────────────────────────
def rank_metrics(ranks):
    ranks = np.array(ranks)
    return {
        "recall@1":  (ranks <= 1).mean(),
        "recall@5":  (ranks <= 5).mean(),
        "recall@10": (ranks <= 10).mean(),
        "MRR":       (1.0 / ranks).mean(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--max-queries-per-journal", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dummy", action="store_true")
    ap.add_argument("--model", default="allenai/specter2_base", help="any sentence-transformers model name")
    ap.add_argument("--adapter", action="store_true", help="SPECTER2 + retrieval adapter (pip install adapters)")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    df = pd.read_csv(CSV_IN, low_memory=False)
    journals, queries = [], []          # queries: (journal_idx_in_list, abstract)

    for path in sorted(glob.glob(os.path.join(CACHE, "row*.json"))):
        row_idx = int(re.search(r"row(\d+)\.json", path).group(1))
        cached = json.load(open(path))
        if not cached["src"].get("status", "").startswith("matched"):
            continue
        works = list(cached["works"])
        if len(works) < 10:
            continue
        rng.shuffle(works)
        n_test = max(2, int(len(works) * args.test_frac))
        test, train = works[:n_test], works[n_test:]
        test_abs = [rebuild_abstract(w.get("abstract_inverted_index")) for w in test]
        test_abs = [a for a in test_abs if len(a.split()) >= 30]
        # skip non-English / garbage abstracts: require mostly Latin letters
        test_abs = [a for a in test_abs if sum(c.isascii() for c in a) / len(a) > 0.95]
        if not test_abs:
            continue

        base = df.loc[row_idx, "journal_text"]
        j = {
            "title": df.loc[row_idx, "Title"],
            "A": str(base),
            "B": build_profile(base, train, n_titles=0)["journal_text_v2"],
            "C": build_profile(base, train, n_titles=5)["journal_text_v2"],
        }
        journals.append(j)
        for a in test_abs[: args.max_queries_per_journal]:
            queries.append((len(journals) - 1, a))

    print(f"Journals in pool : {len(journals)}")
    print(f"Test queries     : {len(queries)} (held-out abstracts)")
    if len(journals) < 20 or len(queries) < 50:
        print("Too little data for a meaningful test — run the pilot on more journals.")
        return

    model = load_model(args)
    label_model = "specter2+adapter" if args.adapter else args.model
    print(f"Encoder          : {label_model}")
    q_emb = embed(model, [q for _, q in queries], "query", args)
    truth = np.array([j for j, _ in queries])

    results, per_variant_ranks = {}, {}
    for v, label in [("A", "A old text"), ("B", "B enriched (no titles)"), ("C", "C enriched + titles")]:
        j_emb = embed(model, [j[v] for j in journals], "doc", args)
        sims = q_emb @ j_emb.T                                   # (queries, journals)
        true_score = sims[np.arange(len(truth)), truth][:, None]
        ranks = (sims > true_score).sum(axis=1) + 1              # 1 = best
        per_variant_ranks[v] = ranks
        results[label] = rank_metrics(ranks)

    out = pd.DataFrame(results).T.round(3)
    print("\n=== RESULTS (pool = pilot journals only; compare rows, not absolute values) ===")
    print(out.to_string())

    # which journals does enrichment help / hurt most?
    d = pd.DataFrame({"journal": [journals[j]["title"] for j in truth],
                      "rank_A": per_variant_ranks["A"], "rank_B": per_variant_ranks["B"]})
    g = d.groupby("journal").mean()
    g["gain"] = g.rank_A - g.rank_B
    print("\nBiggest gains (A→B, lower rank is better):")
    print(g.sort_values("gain", ascending=False).head(5).round(1).to_string())
    print("\nBiggest losses:")
    print(g.sort_values("gain").head(5).round(1).to_string())
    out.to_csv("eval_results_" + re.sub(r"[^A-Za-z0-9]+", "_", label_model) + ".csv")


if __name__ == "__main__":
    main()
