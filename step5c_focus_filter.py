"""
STEP 5c — Domain Focus Filter
Journal Recommendation System

What this module does:
  - Applies an optional focus multiplier on top of hybrid scores
  - User selects a focus (or General / Best Fit for no boost)
  - Confirmed match  → × 1.2 bonus
  - Neutral / unknown → × 1.0 (no change — BERT baseline preserved)
  - Explicit conflict  → × 0.8 penalty

Design rules:
  1. hybrid_score (BERT + BM25) always acts as the foundation
  2. Focus is a nudge, not a replacement
  3. Unranked / Multidisciplinary journals are always neutral
  4. General mode = no multipliers, pure hybrid + risk ranking
"""

# ── Focus options shown in the UI ─────────────────────────────────────────────
FOCUS_OPTIONS = [
    "General / Best Fit",
    "Ethics / Philosophy",
    "Clinical Impact",
    "Legal / Policy",
    "Technical / Engineering",
]

# ── Focus → Areas mapping ─────────────────────────────────────────────────────
# boost    → dataset Areas that get × 1.2
# conflict → dataset Areas that get × 0.8
# anything else (including Unranked, Multidisciplinary) → × 1.0

FOCUS_CONFIG = {
    "Ethics / Philosophy": {
        "boost": [
            "Arts and Humanities",
            "Social Sciences",
            "Psychology",
        ],
        "conflict": [
            "Physics and Astronomy",
            "Chemistry",
            "Materials Science",
            "Chemical Engineering",
            "Engineering",
            "Mathematics",
            "Veterinary",
            "Dentistry",
        ],
        "description": "Boosts journals in Philosophy, Ethics, Social Sciences, and Psychology.",
    },
    "Clinical Impact": {
        "boost": [
            "Medicine",
            "Health Professions",
            "Nursing",
            "Pharmacology. Toxicology and Pharmaceutics",
            "Immunology and Microbiology",
            "Neuroscience",
        ],
        "conflict": [
            "Arts and Humanities",
            "Economics. Econometrics and Finance",
            "Physics and Astronomy",
            "Mathematics",
            "Veterinary",
            "Dentistry",
        ],
        "description": "Boosts clinical and medical journals. Best for patient-facing research.",
    },
    "Legal / Policy": {
        "boost": [
            "Social Sciences",
            "Economics. Econometrics and Finance",
            "Business. Management and Accounting",
            "Decision Sciences",
        ],
        "conflict": [
            "Physics and Astronomy",
            "Chemistry",
            "Materials Science",
            "Chemical Engineering",
            "Veterinary",
            "Agricultural and Biological Sciences",
        ],
        "description": "Boosts law, policy, governance, and economics journals.",
    },
    "Technical / Engineering": {
        "boost": [
            "Computer Science",
            "Engineering",
            "Mathematics",
            "Physics and Astronomy",
            "Materials Science",
            "Energy",
        ],
        "conflict": [
            "Arts and Humanities",
            "Nursing",
            "Veterinary",
            "Dentistry",
            "Psychology",
        ],
        "description": "Boosts CS, Engineering, Math, and Physics journals.",
    },
}

# Multiplier values
BOOST_MULT    = 1.2
NEUTRAL_MULT  = 1.0
CONFLICT_MULT = 0.8


def get_focus_multiplier(journal_areas: str, focus: str) -> tuple[float, str]:
    """
    Returns (multiplier, label) for a journal given the selected focus.

    multiplier: 1.2 / 1.0 / 0.8
    label:      'Boosted' / 'Neutral' / 'Penalized'

    Always returns (1.0, 'Neutral') for:
      - General / Best Fit mode
      - Unranked journals
      - Multidisciplinary journals
    """
    if focus == "General / Best Fit" or focus not in FOCUS_CONFIG:
        return NEUTRAL_MULT, "Neutral"

    # Journals that are always neutral
    neutral_areas = {"Multidisciplinary", "Unranked", ""}
    area_set = set(a.strip() for a in str(journal_areas).split(","))

    if area_set & neutral_areas:
        return NEUTRAL_MULT, "Neutral"

    cfg = FOCUS_CONFIG[focus]

    # Check boost first
    if area_set & set(cfg["boost"]):
        return BOOST_MULT, "Boosted"

    # Check conflict
    if area_set & set(cfg["conflict"]):
        return CONFLICT_MULT, "Penalized"

    # No match either way — neutral
    return NEUTRAL_MULT, "Neutral"


def apply_focus(results, focus: str):
    """
    Applies focus multiplier to hybrid_score for each journal.
    Adds focus_multiplier and focus_label columns.
    Recomputes adjusted_hybrid used downstream by the ranking formula.
    """
    import pandas as pd

    results = results.copy()

    mult_data = results["Areas"].apply(
        lambda areas: get_focus_multiplier(areas, focus)
    )

    results["focus_multiplier"] = [m for m, _ in mult_data]
    results["focus_label"]      = [l for _, l in mult_data]

    # Adjusted hybrid score — this replaces hybrid_score in the ranking
    results["adjusted_hybrid"] = (
        results["hybrid_score"] * results["focus_multiplier"]
    ).round(4)

    return results


def focus_summary(results, focus: str) -> dict:
    """Returns a summary of how many journals were boosted/penalized/neutral."""
    if focus == "General / Best Fit":
        return {"mode": "General", "boosted": 0, "penalized": 0, "neutral": len(results)}

    counts = results["focus_label"].value_counts().to_dict()
    return {
        "mode":      focus,
        "boosted":   counts.get("Boosted", 0),
        "penalized": counts.get("Penalized", 0),
        "neutral":   counts.get("Neutral", 0),
    }
