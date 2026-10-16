"""
apply_quartile_quota.py — make the app show more Q1 journals and fewer Q2/Q3/Q4

Run from the project root (where step3b_bert_rerank.py lives):

    python apply_quartile_quota.py            # apply
    python apply_quartile_quota.py --undo     # restore the .bak backups

What it changes
  1. step3b_bert_rerank.py : hybrid_search() can pick the candidate pool PER QUARTILE
                             (default off, so nothing else changes).
  2. step5_ranking.py      : get_ranked_results() passes that option through.
  3. step6_strategy.py     : build_strategy() asks for 60 Q1 + 10 Q2 + 6 Q3/Q4 candidates,
                             and assign_plans() keeps at most 10 / 2 / 1 per plan.
  4. frontend/src/pages/Results.js : default display limits become 10 / 2 / 1.

Tune the numbers at the top of step6_strategy.py (CANDIDATE_QUOTA, PLAN_LIMITS).
Every edit is an exact-text replacement with a check, so if your copy of a file differs
from what I read, the script stops and changes nothing in that file.
"""
import shutil
import sys

EDITS = {
    "step3b_bert_rerank.py": [
        (
            '    top_n:       int = FINAL_TOP_N,\n) -> "pd.DataFrame":',
            '    top_n:       int = FINAL_TOP_N,\n    quota:       dict = None,\n) -> "pd.DataFrame":',
        ),
        (
            "    top_results = sorted(combined.items(), key=lambda x: -x[1])[:top_n]",
            '''    ranked_all = sorted(combined.items(), key=lambda x: -x[1])
    if quota:
        # Candidate pool PER QUARTILE GROUP: walk down the relevance ranking and keep
        # each journal until its group (Q1 / Q2 / Q3Q4) is full. This stops Q2-Q4
        # journals from using up slots that Q1 journals should get.
        quartiles = df["SJR Best Quartile"].values
        group_of  = lambda q: q if q in ("Q1", "Q2") else "Q3Q4"
        taken     = {"Q1": 0, "Q2": 0, "Q3Q4": 0}
        top_results = []
        for doc_id, score in ranked_all:
            g = group_of(quartiles[doc_id])
            if taken[g] < quota.get(g, 0):
                taken[g] += 1
                top_results.append((doc_id, score))
                if all(taken[k] >= quota.get(k, 0) for k in taken):
                    break
    else:
        top_results = ranked_all[:top_n]''',
        ),
    ],
    "step5_ranking.py": [
        (
            '    top_n: int = 20, focus: str = "General / Best Fit",\n    prestige_weight: float = 1.0\n) -> pd.DataFrame:',
            '    top_n: int = 20, focus: str = "General / Best Fit",\n    prestige_weight: float = 1.0, quota: dict = None\n) -> pd.DataFrame:',
        ),
        (
            "    candidates = hybrid_search(abstract, bm25_index, embeddings, model, df, top_n=top_n)",
            "    candidates = hybrid_search(abstract, bm25_index, embeddings, model, df, top_n=top_n, quota=quota)",
        ),
    ],
    "step6_strategy.py": [
        (
            "def publication_frequency(",
            '''# ── Candidate pool and display limits (tune these) ───────────────────────────
# How many candidates to pull per quartile group BEFORE risk/ranking:
CANDIDATE_QUOTA = {"Q1": 60, "Q2": 10, "Q3Q4": 6}
# Maximum journals shown per plan AFTER ranking:
PLAN_LIMITS     = {"A": 10, "B": 2, "C": 1}


def publication_frequency(''',
        ),
        (
            '        "A": pd.DataFrame(plan_a).reset_index(drop=True),\n        "B": pd.DataFrame(plan_b).reset_index(drop=True),\n        "C": pd.DataFrame(plan_c).reset_index(drop=True),',
            '        "A": pd.DataFrame(plan_a[:PLAN_LIMITS["A"]]).reset_index(drop=True),\n        "B": pd.DataFrame(plan_b[:PLAN_LIMITS["B"]]).reset_index(drop=True),\n        "C": pd.DataFrame(plan_c[:PLAN_LIMITS["C"]]).reset_index(drop=True),',
        ),
        (
            "                                top_n=30, focus=focus, prestige_weight=prestige_weight)",
            "                                top_n=30, focus=focus, prestige_weight=prestige_weight,\n                                quota=CANDIDATE_QUOTA)",
        ),
    ],
    "frontend/src/pages/Results.js": [
        (
            "        const limit = planKey === 'C' ? 5 : 3;",
            "        const limit = planKey === 'A' ? 10 : planKey === 'B' ? 2 : 1;",
        ),
    ],
}


def main():
    undo = "--undo" in sys.argv
    if undo:
        for path in EDITS:
            try:
                shutil.copyfile(path + ".bak", path)
                print(f"restored {path}")
            except FileNotFoundError:
                print(f"no backup for {path}")
        return

    # check everything first, so we never half-apply
    new_text = {}
    for path, edits in EDITS.items():
        try:
            text = open(path, encoding="utf-8").read()
        except FileNotFoundError:
            sys.exit(f"STOP: {path} not found — run this from the project root.")
        if all(new in text for _, new in edits):      # every replacement already present
            print(f"skip  {path} (already patched)")
            continue
        for old, _ in edits:
            if text.count(old) != 1:
                sys.exit(f"STOP: in {path} I expected to find this exactly once, found {text.count(old)}:\n"
                         f"    {old.strip().splitlines()[0][:100]}\n"
                         f"Your file differs from the version I read. Nothing was changed.")
        for old, new in edits:
            text = text.replace(old, new)
        new_text[path] = text

    for path, text in new_text.items():
        shutil.copyfile(path, path + ".bak")
        open(path, "w", encoding="utf-8").write(text)
        print(f"patched {path}  (backup: {path}.bak)")
    print("\nDone. Restart the ML service (and rebuild/restart the frontend) to see the change.")


if __name__ == "__main__":
    main()
