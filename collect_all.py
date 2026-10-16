"""
collect_all.py — collect OpenAlex profile data for ALL journals, then build journal_text_v2

Two modes:
  python collect_all.py                 # COLLECT: resumable, stops at a daily budget
  python collect_all.py --build         # BUILD  : writes journals_clean_v2.csv

COLLECT
  - For every journal in journals_clean.csv: resolve OpenAlex source (ISSN first,
    title-search fallback), fetch the most recent papers, and store a COMPACT summary
    (top keywords/topics with counts + a few Latin-script titles) in
    collected/profiles.jsonl — one line per journal, appended as it goes.
  - Re-running skips journals already done, so you can stop/restart any time.
  - Stops cleanly when the per-run budget is reached (default 9000 units).
    Cost model: filtered list call = 1 unit, title search = 10 units, ISSN lookup = 0.
    At ~$0.0001/unit that is ~$0.90/run, under the $1/day free allowance — check
    openalex.org/pricing, as these numbers may change.

BUILD
  - Reads collected/profiles.jsonl and writes journals_clean_v2.csv: the SAME rows in
    the SAME order as journals_clean.csv (so existing embeddings stay aligned), plus
    journal_text_v2, oa_match_status, oa_n_papers.
  - Journals with no profile keep their old text in journal_text_v2.

Usage:
    export OPENALEX_API_KEY=your_key
    python collect_all.py --limit 20            # small test first
    python collect_all.py                       # then run daily until it says DONE
    python collect_all.py --build

Needs openalex_pilot.py in the same folder (reuses its helper functions).
Written without live API access: test with --limit 20 before the full run.
"""

import argparse
import json
import os
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openalex_pilot import split_issns, title_sim, is_latin  # noqa: E402

API = "https://api.openalex.org"
CSV_IN = "journals_clean.csv"
CSV_OUT = "journals_clean_v2.csv"
OUT_DIR = "collected"
PROFILES = os.path.join(OUT_DIR, "profiles.jsonl")
MAX_CHARS = 1800          # same cap as the tested variant (keeps under SPECTER2's 512 tokens)
FINAL = {"matched", "matched_title", "no_match"}   # statuses that never need retrying


class BudgetStop(Exception):
    pass


# ── Budgeted HTTP ────────────────────────────────────────────────────────────
class Budget:
    def __init__(self, max_units):
        self.max, self.used, self.lock = max_units, 0, threading.Lock()
        self.stopped = False

    def spend(self, units):
        with self.lock:
            if self.stopped or self.used + units > self.max:
                self.stopped = True
                raise BudgetStop()
            self.used += units


def api_get(url, params, retries=5):
    """GET with backoff. Returns json, None for 404. Raises BudgetStop on quota errors."""
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            return None
        if r.status_code in (402, 403):           # key/quota problem — don't hammer
            raise BudgetStop()
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(min(2 ** attempt * 2, 60))
            continue
        r.raise_for_status()
    if r is not None and r.status_code == 429:    # still rate-limited after retries
        raise BudgetStop()
    return None


# ── Per-journal collection ───────────────────────────────────────────────────
def resolve_source(title, issn_field, key, budget):
    base = {"api_key": key} if key else {}
    best = None
    for issn in split_issns(issn_field):
        data = api_get(f"{API}/sources/issn:{issn}", dict(base))          # singleton: free
        if not data:
            continue
        sim = title_sim(title, data.get("display_name", ""))
        if best is None or sim > best["sim"]:
            best = {"id": data["id"].rsplit("/", 1)[-1], "name": data.get("display_name", ""),
                    "sim": round(sim, 3)}
    if best:
        best["status"] = "matched"
        best["review"] = bool(best["sim"] < 0.3 and is_latin(title) and is_latin(best["name"]))
        return best

    budget.spend(10)                                                      # search is ~10x
    data = api_get(f"{API}/sources", {**base, "search": title, "per_page": 5,
                                      "select": "id,display_name,works_count"})
    cands = [(title_sim(title, r.get("display_name", "")), r)
             for r in (data or {}).get("results", [])]
    cands = [c for c in cands if c[0] >= 0.85 and (c[1].get("works_count") or 0) > 0]
    if cands:
        sim, r = max(cands, key=lambda c: c[0])
        return {"id": r["id"].rsplit("/", 1)[-1], "name": r.get("display_name", ""),
                "sim": round(sim, 3), "status": "matched_title", "review": False}
    return {"status": "no_match"}


def fetch_works(source_id, since, per_journal, key, budget):
    budget.spend(1)
    params = {
        "filter": f"primary_location.source.id:{source_id},"
                  f"from_publication_date:{since}-01-01,type:article",
        "sort": "publication_date:desc",
        "per_page": min(per_journal, 200),
        "select": "id,title,keywords,topics",       # no abstracts: keeps responses small
    }
    if key:
        params["api_key"] = key
    return (api_get(f"{API}/works", params) or {}).get("results", [])


def summarise(works, top_kw=30, top_topics=15, n_titles=10):
    kw, tp = Counter(), Counter()
    for w in works:
        kw.update(k["display_name"] for k in (w.get("keywords") or []) if k.get("display_name"))
        tp.update(t["display_name"] for t in (w.get("topics") or []) if t.get("display_name"))
    titles = [w["title"] for w in works if w.get("title") and is_latin(w["title"])][:n_titles]
    return {"n_papers": len(works), "keywords": kw.most_common(top_kw),
            "topics": tp.most_common(top_topics), "titles": titles}


def collect_one(row_idx, title, issn_field, args, key, budget):
    try:
        src = resolve_source(title, issn_field, key, budget)
        rec = {"row": row_idx, "status": src["status"], "oa_name": src.get("name", ""),
               "sim": src.get("sim"), "review": src.get("review", False)}
        if src["status"].startswith("matched"):
            works = fetch_works(src["id"], args.since, args.per_journal, key, budget)
            rec.update(summarise(works))
        return rec
    except BudgetStop:
        raise
    except Exception as e:                           # one bad journal must not kill the run
        return {"row": row_idx, "status": "error", "error": str(e)[:200]}


# ── Text composition (same recipe as the tested variant C) ───────────────────
def compose_text(base, rec, top_kw=15, top_topics=8, n_titles=5):
    text = str(base)
    if rec.get("topics"):
        text += ". topics: " + ", ".join(t for t, _ in rec["topics"][:top_topics])
    if rec.get("keywords"):
        text += ". keywords: " + ", ".join(k for k, _ in rec["keywords"][:top_kw])
    titles = rec.get("titles", [])[:n_titles]
    if titles:
        tpart = ". recent titles: "
        for t in titles:
            add = ("" if tpart.endswith(": ") else " | ") + t
            if len(text) + len(tpart) + len(add) > MAX_CHARS:
                break
            tpart += add
        if not tpart.endswith(": "):
            text += tpart
    return text.lower()[:MAX_CHARS]


# ── Modes ────────────────────────────────────────────────────────────────────
def load_done():
    done, latest = set(), {}
    if os.path.exists(PROFILES):
        for line in open(PROFILES, encoding="utf-8"):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue                              # half-written last line after a crash
            latest[rec["row"]] = rec                  # later lines win
        done = {r for r, rec in latest.items() if rec["status"] in FINAL}
    return done, latest


def run_collect(args):
    key = os.environ.get("OPENALEX_API_KEY", "")
    if not key:
        print("Warning: OPENALEX_API_KEY not set — OpenAlex requires a key.\n")
    os.makedirs(OUT_DIR, exist_ok=True)
    df = pd.read_csv(CSV_IN, low_memory=False)
    done, _ = load_done()
    todo = [i for i in range(len(df)) if i not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(df)} journals | {len(done)} already done | {len(todo)} to do this run")

    budget = Budget(args.max_units)
    n = 0
    with open(PROFILES, "a", encoding="utf-8") as out, ThreadPoolExecutor(args.workers) as pool:
        for start in range(0, len(todo), args.workers * 4):          # small batches → fast stop
            batch = todo[start:start + args.workers * 4]
            futs = [pool.submit(collect_one, i, df.at[i, "Title"], df.at[i, "Issn"], args, key, budget)
                    for i in batch]
            stopped = False
            for f in futs:
                try:
                    rec = f.result()
                except BudgetStop:
                    stopped = True
                    continue
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                n += 1
                if n % 100 == 0:
                    print(f"  {n} journals collected  (units used: {budget.used})")
            if stopped or budget.stopped:
                print("\nBudget/quota limit reached — progress is saved. Re-run later to continue.")
                break
            time.sleep(args.pause)

    done, latest = load_done()
    left = len(df) - len(done)
    st = Counter(r["status"] for r in latest.values())
    print(f"\nThis run: {n} journals | units used: {budget.used} (~${budget.used * 0.0001:.2f})")
    print(f"Status so far: {dict(st)}")
    print("DONE — now run: python collect_all.py --build" if left == 0
          else f"{left} journals remaining — re-run to continue.")


def run_build(args):
    df = pd.read_csv(CSV_IN, low_memory=False)
    _, latest = load_done()
    texts, status, npap = [], [], []
    for i in range(len(df)):
        rec = latest.get(i)
        if rec and rec["status"].startswith("matched") and rec.get("n_papers", 0) > 0:
            texts.append(compose_text(df.at[i, "journal_text"], rec))
        else:
            texts.append(str(df.at[i, "journal_text"]))
        status.append(rec["status"] if rec else "not_collected")
        npap.append(rec.get("n_papers", 0) if rec else 0)
    out = df.copy()
    out["journal_text_v2"] = texts
    out["oa_match_status"] = status
    out["oa_n_papers"] = npap
    assert len(out) == len(df)
    out.to_csv(CSV_OUT, index=False)
    enriched = sum(t != str(b) for t, b in zip(texts, df["journal_text"]))
    print(f"Wrote {CSV_OUT}: {len(out)} rows (same order as {CSV_IN})")
    print(f"Enriched: {enriched} | unchanged: {len(out) - enriched}")
    print(pd.Series(status).value_counts().to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--since", type=int, default=2020)
    ap.add_argument("--per-journal", type=int, default=100)
    ap.add_argument("--max-units", type=int, default=9000, help="budget per run (see docstring)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--pause", type=float, default=0.2, help="seconds between batches")
    ap.add_argument("--limit", type=int, default=0, help="only process N journals (testing)")
    args = ap.parse_args()
    run_build(args) if args.build else run_collect(args)


if __name__ == "__main__":
    main()
