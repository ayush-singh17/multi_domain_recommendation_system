"""
ML Service — FastAPI
Journal Recommendation System

This service wraps the entire Python ML pipeline and exposes it as a REST API.
Django backend calls this service — it never talks to the ML pipeline directly.

Endpoints:
  GET  /health          → check if model is loaded and ready
  POST /recommend       → returns Plan A/B/C with explanations
  POST /pdf             → returns PDF report as file download

Run with:
  uvicorn main:app --host 0.0.0.0 --port 8001 --reload

Keep this running separately from Django.
"""

import sys
import os

# ── Add parent directory to path so we can import pipeline scripts ────────────
# ml_service/ is inside journal_finder_app/ where all step*.py files live
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PARENT_DIR)

# Change working directory to parent so all file reads (csv, pkl, npy) work
os.chdir(PARENT_DIR)

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
# Add utils/ to path so we can import get_journal_link
_utils_path = os.path.join(PARENT_DIR, 'utils')
if _utils_path not in sys.path:
    sys.path.insert(0, _utils_path)
from journal_links import get_journal_link


# ── Helpers ──────────────────────────────────────────────────────────────────
import math

def clean_value(v):
    """Convert nan/inf to None so JSON serialisation never fails."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def sanitise(v):
    """Recursively clean nan/inf from any value for JSON safety."""
    if isinstance(v, dict):
        return {k: sanitise(val) for k, val in v.items()}
    if isinstance(v, list):
        return [sanitise(i) for i in v]
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


# ── Request / Response schemas ────────────────────────────────────────────────

class RecommendRequest(BaseModel):
    abstract:        str   = ""          # used in abstract mode
    keywords:        list  = []           # used in keyword mode
    search_mode:     str   = "abstract"  # "abstract" | "keyword"
    focus:           str   = "General / Best Fit"
    prestige_weight: float = 1.0   # 1.0=prestige, 0.0=speed, 0.5=balanced


def keywords_to_abstract(keywords: list) -> str:
    """
    Expands a list of keywords into a fluent pseudo-abstract sentence
    so the BM25 + BERT pipeline receives natural language rather than
    a bare comma-separated list, which improves embedding quality.

    Example:
      ["machine learning", "drug discovery", "protein folding"]
      -> "This research focuses on machine learning, drug discovery, and
          protein folding. The study investigates related concepts,
          methods, and applications in these areas."
    """
    if not keywords:
        return ""
    clean = [k.strip() for k in keywords if k.strip()]
    if not clean:
        return ""
    if len(clean) == 1:
        joined = clean[0]
    elif len(clean) == 2:
        joined = f"{clean[0]} and {clean[1]}"
    else:
        joined = ", ".join(clean[:-1]) + f", and {clean[-1]}"
    return (
        f"This research focuses on {joined}. "
        f"The study investigates related concepts, methods, and applications "
        f"in these areas, examining their theoretical foundations and "
        f"practical implications for advancing knowledge in these fields."
    )


class PDFRequest(BaseModel):
    abstract:        str   = ""
    keywords:        list  = []
    search_mode:     str   = "abstract"
    focus:           str   = "General / Best Fit"
    prestige_weight: float = 1.0


# ── Global state — loaded once at startup ─────────────────────────────────────
# This is the equivalent of Streamlit's @st.cache_resource

_resources = {}


def load_pipeline():
    """
    Loads all ML resources into memory once at startup.
    After this, every request is fast — no reloading.
    """
    print("Loading pipeline resources...")

    from step5_ranking import load_resources
    df, bm25_index, embeddings, model = load_resources()

    _resources["df"]         = df
    _resources["bm25_index"] = bm25_index
    _resources["embeddings"] = embeddings
    _resources["model"]      = model
    _resources["ready"]      = True

    # Load trends data
    import pandas as pd
    trends_path = os.path.join(PARENT_DIR, "journal_trends.csv")
    if os.path.exists(trends_path):
        trends_df = pd.read_csv(trends_path)
        # Build ISSN lookup
        lookup = {}
        for _, row in trends_df.iterrows():
            for issn in str(row["Issn"]).replace("-","").split(","):
                issn = issn.strip()
                if issn:
                    lookup[issn] = row.to_dict()
        _resources["trends_lookup"] = lookup
        print(f"Trends loaded: {len(trends_df):,} journals")
    else:
        _resources["trends_lookup"] = {}
        print("Trends file not found — run build_trends.py first")

    print("Pipeline ready.")


# ── App lifecycle ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup — load everything into memory
    load_pipeline()
    yield
    # Runs at shutdown — nothing to clean up
    print("ML service shutting down.")


app = FastAPI(
    title="Journal Recommendation ML Service",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow Django backend and React frontend to call this service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Check if the ML service is loaded and ready."""
    return {
        "status":  "ready" if _resources.get("ready") else "loading",
        "journals": len(_resources["df"]) if "df" in _resources else 0,
    }


def _get_trend(issn_str: str) -> dict | None:
    """Look up trend data for a journal by ISSN."""
    lookup = _resources.get("trends_lookup", {})
    if not lookup:
        return None
    for issn in str(issn_str).replace("-", "").split(","):
        issn = issn.strip()
        if issn in lookup:
            row = lookup[issn]
            years = [2020, 2021, 2022, 2023, 2024]
            citations = [row.get(f"citations_{y}") for y in years]
            return sanitise({
                "direction": row.get("trend_direction"),
                "pct":       row.get("trend_pct"),
                "years":     years,
                "citations": citations,
            })
    return None


@app.post("/recommend")
def recommend(req: RecommendRequest):
    """
    Takes an abstract and optional focus filter.
    Returns Plan A, B, C with journal details and explanations.
    """
    if not _resources.get("ready"):
        raise HTTPException(status_code=503, detail="ML service still loading")

    # ── Resolve the text to search with ─────────────────────────────────────
    if req.search_mode == "keyword":
        if not req.keywords:
            raise HTTPException(status_code=400, detail="At least one keyword is required")
        search_text = keywords_to_abstract(req.keywords)
    else:
        search_text = req.abstract.strip()
        if not search_text:
            raise HTTPException(status_code=400, detail="Abstract cannot be empty")

    word_count = len(search_text.split())
    warnings = []
    # Only apply word-count warnings in abstract mode
    if req.search_mode == "abstract":
        if word_count < 30:
            warnings.append(f"Abstract is very short ({word_count} words). Results may be less accurate.")
        elif word_count < 60:
            warnings.append(f"Abstract is {word_count} words. A full abstract gives better results.")

    try:
        from step6_strategy import build_strategy, PLAN_META
        from step7_explain  import explain_strategy

        df         = _resources["df"]
        bm25_index = _resources["bm25_index"]
        embeddings = _resources["embeddings"]
        model      = _resources["model"]

        strategy  = build_strategy(search_text, df, bm25_index, embeddings, model,
                                    focus=req.focus, prestige_weight=req.prestige_weight)
        explained = explain_strategy(strategy, search_text, df, search_mode=req.search_mode)

        # ── Collect all journals across plans for concurrent link fetching ──
        all_titles = []
        for plan_key in ["A", "B", "C"]:
            for exp in explained.get(plan_key, []):
                all_titles.append(exp["title"])

        # Fetch homepage URLs concurrently (max 10 workers) — avoids serial latency
        link_map = {}  # title -> url | None
        with ThreadPoolExecutor(max_workers=10) as pool:
            future_to_title = {pool.submit(get_journal_link, t): t for t in all_titles}
            for future in as_completed(future_to_title):
                title = future_to_title[future]
                try:
                    link_map[title] = future.result()
                except Exception:
                    link_map[title] = None

        # Serialise to plain dicts for JSON response
        plans = {}
        for plan_key in ["A", "B", "C"]:
            options = explained.get(plan_key, [])
            plans[plan_key] = []
            for exp in options:
                plans[plan_key].append(sanitise({
                    "title":          exp["title"],
                    "quartile":       exp["quartile"],
                    "risk_level":     exp["risk_level"],
                    "final_score":    exp["final_score"],
                    "h_index":        exp["h_index"],
                    "sjr":            exp["sjr"],
                    "publisher":      exp["publisher"],
                    "coverage":       exp["coverage"],
                    "issn":           exp["issn"],
                    "areas":          exp["areas"],
                    "open_access":    exp["open_access"],
                    "matched_tokens": exp["matched_tokens"],
                    "relevance":      exp["relevance"],
                    "risk_signals":   exp["risk_signals"],
                    "score_breakdown":exp["score_breakdown"],
                    "apc_usd":        exp.get("apc_usd"),
                    "apc_currency":   exp.get("apc_currency"),
                    "citescore":      exp.get("citescore"),
                    "impact_factor":  exp.get("impact_factor"),
                    "trend":            _get_trend(exp.get("issn", "")),
                    "weeks_to_publish":  exp.get("weeks_to_publish"),
                    "months_to_publish": exp.get("months_to_publish"),
                    "in_doaj":           exp.get("in_doaj"),
                    "predatory_score":   exp.get("predatory_score"),
                    "predatory_level":   exp.get("predatory_level"),
                    "predatory_flags":   exp.get("predatory_flags"),
                    "homepage_url":       link_map.get(exp["title"]),
                    "mahe_approved":     exp.get("mahe_approved", 0),
                }))

        # Stats
        ranked   = strategy["ranked"]
        total    = len(ranked)
        q1_count = int((ranked["Quartile"] == "Q1").sum())
        low_risk = int((ranked["risk_level"] == "Low").sum())

        # Build submission timeline
        from timeline_calculator import build_timeline
        timeline = build_timeline(plans)

        return sanitise({
            "plans":       plans,
            "stats": {
                "total":    total,
                "q1_count": q1_count,
                "low_risk": low_risk,
            },
            "focus":       req.focus,
            "warnings":    warnings,
            "timeline":    timeline,
            "search_mode": req.search_mode,
            "keywords":    req.keywords if req.search_mode == "keyword" else [],
        })

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trends/{issn}")
def get_trends(issn: str):
    """
    GET /trends/<issn>
    Returns 5-year trend data for a journal by ISSN.
    """
    if not _resources.get("ready"):
        raise HTTPException(status_code=503, detail="ML service still loading")

    lookup = _resources.get("trends_lookup", {})
    clean  = issn.replace("-", "").strip()
    data   = lookup.get(clean)

    if not data:
        raise HTTPException(status_code=404, detail="Journal not found in trends data")

    years = [2020, 2021, 2022, 2023, 2024]
    return sanitise({
        "title":      data["Title"],
        "issn":       data["Issn"],
        "trend_direction": data["trend_direction"],
        "trend_pct":  data["trend_pct"],
        "years":      years,
        "citations":  [data.get(f"citations_{y}") for y in years],
        "sjr":        [data.get(f"sjr_{y}")        for y in years],
        "docs":       [data.get(f"docs_{y}")        for y in years],
    })


@app.post("/pdf")
def generate_pdf_endpoint(req: PDFRequest):
    """
    Takes an abstract and focus.
    Returns a PDF report as a file download.
    """
    if not _resources.get("ready"):
        raise HTTPException(status_code=503, detail="ML service still loading")

    # Resolve search text based on mode
    if req.search_mode == "keyword":
        if not req.keywords:
            raise HTTPException(status_code=400, detail="At least one keyword is required")
        search_text = keywords_to_abstract(req.keywords)
    else:
        search_text = req.abstract.strip()
        if not search_text:
            raise HTTPException(status_code=400, detail="Abstract cannot be empty")

    try:
        from step6_strategy import build_strategy
        from step7_explain  import explain_strategy
        from generate_pdf   import generate_report
        from datetime       import datetime

        df         = _resources["df"]
        bm25_index = _resources["bm25_index"]
        embeddings = _resources["embeddings"]
        model      = _resources["model"]

        strategy  = build_strategy(search_text, df, bm25_index, embeddings, model,
                                    focus=req.focus, prestige_weight=req.prestige_weight)
        explained = explain_strategy(strategy, search_text, df, search_mode=req.search_mode)

        # Inject trend data into each journal before PDF generation
        for plan_key, options in explained.items():
            for exp in options:
                if "issn" in exp and exp.get("trend") is None:
                    exp["trend"] = _get_trend(exp.get("issn", ""))
                    # weeks_to_publish comes from the df via step3b — already in exp

        pdf_buf   = generate_report(
            explained, strategy, search_text, req.focus,
            search_mode=req.search_mode,
            keywords=req.keywords if req.search_mode == "keyword" else None,
        )

        date_str  = datetime.now().strftime("%Y%m%d_%H%M")
        filename  = f"journal_recommendations_{date_str}.pdf"

        return StreamingResponse(
            pdf_buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Trigger reload for parent module change: step6_strategy updated to unsliced plans.

