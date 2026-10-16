"""
openalex_pilot.py — pilot for enriching journal descriptions from OpenAlex

What it does (for N randomly sampled journals from journals_clean.csv):
  1. Resolves each journal to an OpenAlex source by ISSN (trusted as an exact id),
     falling back to a title search when no ISSN matches.
  2. Pulls the most recent works for that source (title, keywords, topics, abstract).
  3. Builds a richer text field `journal_text_v2` = existing journal_text
     + top keywords + top topics + a few recent titles.
  4. Writes pilot_profiles.csv and prints a summary (match rate, coverage, cost).

Raw API responses are cached in pilot_cache/ so re-runs cost nothing.

Usage:
    export OPENALEX_API_KEY=your_key        # free key: openalex.org/settings/api
    python openalex_pilot.py --n 200 --since 2020 --per-journal 100

NOTE: written without live access to the OpenAlex API. Run with --n 5 first and
check pilot_cache/ to confirm the field names before running the full pilot.
"""

import argparse
import difflib
import json
import os
import re
import sys
import time
from collections import Counter

import pandas as pd
import requests

API = "https://api.openalex.org"
CSV_IN = "journals_clean.csv"
CACHE = "pilot_cache"
WORK_FIELDS = "id,title,publication_year,keywords,topics,abstract_inverted_index"

CALLS = {"source": 0, "works": 0}


# ── HTTP with retry ──────────────────────────────────────────────────────────
def http_get(url, params, retries=4):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt * 2)
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
    return None


# ── Helpers ──────────────────────────────────────────────────────────────────
def split_issns(raw):
    """'00079235, 15424863' -> ['0007-9235', '1542-4863']"""
    out = []
    for part in str(raw).split(","):
        d = re.sub(r"[^0-9Xx]", "", part).upper()
        if len(d) == 8:
            out.append(f"{d[:4]}-{d[4:]}")
    return out


def norm_title(t):
    return re.sub(r"[^a-z0-9 ]", "", str(t).lower().replace("&", "and")).strip()


def title_sim(a, b):
    return difflib.SequenceMatcher(None, norm_title(a), norm_title(b)).ratio()


def rebuild_abstract(inv):
    """OpenAlex gives abstracts as {word: [positions]} — turn back into text."""
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def cache_path(key):
    os.makedirs(CACHE, exist_ok=True)
    return os.path.join(CACHE, f"{key}.json")


# ── OpenAlex lookups ─────────────────────────────────────────────────────────
def is_latin(text, min_ratio=0.7):
    """True if most letters are Latin-script (filters Chinese/Russian/Persian/etc)."""
    letters = [c for c in str(text) if c.isalpha()]
    if not letters:
        return False
    latin = sum(1 for c in letters if ord(c) < 0x250)   # Basic Latin + Latin extended
    return latin / len(letters) >= min_ratio


def resolve_source(title, issn_field, api_key, min_sim):
    """
    1) ISSN lookup. An ISSN is an exact identifier, so a match is TRUSTED even when
       the names differ (renames, translations, subtitles, non-Latin scripts).
       We still record title_sim and flag Latin-vs-Latin low-similarity for review.
    2) If no ISSN matches, fall back to a title search and require a close title.
    """
    best = None
    for issn in split_issns(issn_field):
        CALLS["source"] += 1
        data = http_get(f"{API}/sources/issn:{issn}", {"api_key": api_key} if api_key else {})
        if not data:
            continue
        sim = title_sim(title, data.get("display_name", ""))
        if best is None or sim > best["sim"]:
            best = {"id": data["id"].rsplit("/", 1)[-1],
                    "name": data.get("display_name", ""),
                    "works_count": data.get("works_count"),
                    "sim": round(sim, 3), "issn": issn}
    if best:
        best["status"] = "matched"
        best["review"] = bool(best["sim"] < 0.3 and is_latin(title) and is_latin(best["name"]))
        return best

    # Fallback: title search (a 'search' call costs ~10x a normal call, but few journals need it)
    CALLS["source"] += 1
    params = {"search": title, "per_page": 5, "select": "id,display_name,works_count"}
    if api_key:
        params["api_key"] = api_key
    data = http_get(f"{API}/sources", params)
    cands = []
    for r in (data or {}).get("results", []):
        cands.append((title_sim(title, r.get("display_name", "")), r))
    cands = [c for c in cands if c[0] >= 0.85 and (c[1].get("works_count") or 0) > 0]
    if cands:
        sim, r = max(cands, key=lambda c: c[0])
        return {"id": r["id"].rsplit("/", 1)[-1], "name": r.get("display_name", ""),
                "works_count": r.get("works_count"), "sim": round(sim, 3),
                "status": "matched_title", "review": False}
    return {"status": "no_match"}


def fetch_works(source_id, since, per_journal, api_key):
    CALLS["works"] += 1
    params = {
        "filter": f"primary_location.source.id:{source_id},"
                  f"from_publication_date:{since}-01-01,type:article",
        "sort": "publication_date:desc",
        "per_page": min(per_journal, 200),
        "select": WORK_FIELDS,
    }
    if api_key:
        params["api_key"] = api_key
    data = http_get(f"{API}/works", params)
    return (data or {}).get("results", [])


# ── Profile building ─────────────────────────────────────────────────────────
MAX_CHARS = 1800   # ~450 tokens; SPECTER2 truncates at 512 tokens, so stay under


def build_profile(base_text, works, top_kw=15, top_topics=8, n_titles=5):
    kw, topics = Counter(), Counter()
    n_abs = n_kw = 0
    for w in works:
        ks = [k.get("display_name") for k in (w.get("keywords") or []) if k.get("display_name")]
        ts = [t.get("display_name") for t in (w.get("topics") or []) if t.get("display_name")]
        kw.update(ks)
        topics.update(ts)
        n_kw += bool(ks)
        n_abs += bool(w.get("abstract_inverted_index"))
    # keep only Latin-script titles (SPECTER2 is English-oriented)
    titles = [w["title"] for w in works if w.get("title") and is_latin(w["title"])][:n_titles]
    top_k = [k for k, _ in kw.most_common(top_kw)]
    top_t = [t for t, _ in topics.most_common(top_topics)]

    # order = most reliable signal first, titles last so they are cut first
    text = str(base_text)
    if top_t:
        text += ". topics: " + ", ".join(top_t)
    if top_k:
        text += ". keywords: " + ", ".join(top_k)
    if titles:
        tpart = ". recent titles: "
        for t in titles:
            add = ("" if tpart.endswith(": ") else " | ") + t
            if len(text) + len(tpart) + len(add) > MAX_CHARS:
                break
            tpart += add
        if not tpart.endswith(": "):
            text += tpart
    return {
        "n_papers": len(works),
        "n_with_abstract": n_abs,
        "n_with_keywords": n_kw,
        "top_keywords": "; ".join(top_k),
        "top_topics": "; ".join(top_t),
        "journal_text_v2": text.lower()[:MAX_CHARS],
    }


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--since", type=int, default=2020)
    ap.add_argument("--per-journal", type=int, default=100)
    ap.add_argument("--min-title-sim", type=float, default=0.6)
    ap.add_argument("--out", default="pilot_profiles.csv")
    args = ap.parse_args()

    api_key = os.environ.get("OPENALEX_API_KEY", "")
    if not api_key:
        print("Warning: OPENALEX_API_KEY not set — OpenAlex now requires a key; calls may fail.\n")

    df = pd.read_csv(CSV_IN, low_memory=False)
    sample = df.sample(n=min(args.n, len(df)), random_state=args.seed)

    rows = []
    for i, (idx, j) in enumerate(sample.iterrows(), 1):
        key = f"row{idx}"
        cp = cache_path(key)
        cached = json.load(open(cp)) if os.path.exists(cp) else None
        if cached and cached["src"].get("status") == "title_mismatch":
            # older run rejected these on name; the ISSN match is trusted, so accept
            src = cached["src"]
            src["status"], src["review"] = "matched", False
            works = fetch_works(src["id"], args.since, args.per_journal, api_key)
            json.dump({"src": src, "works": works}, open(cp, "w"))
        elif cached and cached["src"].get("status") not in ("no_issn_match", "no_match"):
            src, works = cached["src"], cached["works"]
        else:
            src = resolve_source(j["Title"], j["Issn"], api_key, args.min_title_sim)
            works = []
            if src["status"].startswith("matched"):
                works = fetch_works(src["id"], args.since, args.per_journal, api_key)
            json.dump({"src": src, "works": works}, open(cp, "w"))

        prof = build_profile(j["journal_text"], works)
        rows.append({
            "row": idx, "Title": j["Title"], "Quartile": j.get("SJR Best Quartile"),
            "Areas": j.get("Areas"), "match_status": src["status"],
            "oa_name": src.get("name", ""), "title_sim": src.get("sim", ""),
            "oa_works_count": src.get("works_count", ""), "review": src.get("review", ""), **prof,
        })
        if i % 20 == 0:
            print(f"  {i}/{len(sample)} journals done")

    out = pd.DataFrame(rows)
    out.to_csv(args.out, index=False)

    # ── Summary ──────────────────────────────────────────────────────────────
    n = len(out)
    matched = out[out.match_status.str.startswith("matched")]
    print("\n=== PILOT SUMMARY ===")
    print(f"Journals sampled        : {n}")
    print(out.match_status.value_counts().to_string())
    print(f"Match rate              : {len(matched)/n*100:.1f}%")
    if len(matched):
        tot = matched.n_papers.sum()
        print(f"Papers fetched          : {tot} (avg {matched.n_papers.mean():.0f}/journal)")
        print(f"Papers with abstract    : {matched.n_with_abstract.sum()/max(tot,1)*100:.1f}%")
        print(f"Papers with keywords    : {matched.n_with_keywords.sum()/max(tot,1)*100:.1f}%")
        print(f"Journals with <10 papers: {(matched.n_papers < 10).sum()}")
    print(f"API calls               : {CALLS['source']} source + {CALLS['works']} works")
    print(f"Wrote {args.out}. Check rows where review=True and the no_match rows.")


if __name__ == "__main__":
    sys.exit(main())
