"""
Timeline Calculator
Journal Recommendation System

Calculates realistic submission timelines for the A → B → C strategy.
Uses real DOAJ weeks_to_publish data where available,
falls back to quartile-based estimates where not.

Estimates include:
  - Per-journal review time
  - Optimistic / Realistic / Worst-case total timelines
  - Plain language advice per scenario
"""

# ── Fallback estimates (weeks) when DOAJ data not available ──────────────────
# Based on industry knowledge + our dataset quartile averages
QUARTILE_FALLBACK = {
    "Q1":       20,
    "Q2":       16,
    "Q3":       12,
    "Q4":       10,
    "Unranked": 10,
}

# Preparation time between submissions (rewriting, reformatting) in weeks
REVISION_WEEKS = 2


def get_review_weeks(journal: dict) -> tuple:
    """
    Returns (weeks, is_estimated) for a journal.
    Uses real DOAJ data if available, otherwise quartile fallback.
    """
    weeks = journal.get("weeks_to_publish")
    try:
        if weeks is not None and str(weeks) not in ("None", "nan", ""):
            return round(float(weeks)), False
    except:
        pass

    quartile = journal.get("quartile", "Q2")
    return QUARTILE_FALLBACK.get(quartile, 16), True


def weeks_to_display(weeks: int) -> str:
    months = round(weeks / 4.33, 1)
    return f"~{weeks} weeks (~{months} months)"


def build_timeline(plans: dict) -> dict:
    """
    Builds the full submission timeline from the strategy plans.

    plans: dict with keys 'A', 'B', 'C' each containing a list of journal dicts

    Returns a timeline dict with:
      - per_plan: details for each plan's top journal
      - scenarios: optimistic / realistic / worst_case totals
      - advice: plain language recommendation
    """
    per_plan = {}

    for plan_key in ["A", "B", "C"]:
        journals = plans.get(plan_key, [])
        if not journals:
            per_plan[plan_key] = None
            continue

        top = journals[0]
        weeks, estimated = get_review_weeks(top)

        per_plan[plan_key] = {
            "title":       top.get("title", ""),
            "quartile":    top.get("quartile", ""),
            "weeks":       weeks,
            "is_estimated":estimated,
            "display":     weeks_to_display(weeks),
            "source":      "DOAJ data" if not estimated else "Estimated from quartile",
        }

    # ── Scenario calculations ─────────────────────────────────────────────
    a = per_plan.get("A")
    b = per_plan.get("B")
    c = per_plan.get("C")

    scenarios = {}

    # Optimistic: accepted at Plan A on first try
    if a:
        scenarios["optimistic"] = {
            "label":   "Optimistic",
            "desc":    f"Accepted at {a['title'][:40]}{'...' if len(a['title']) > 40 else ''}",
            "weeks":   a["weeks"],
            "display": weeks_to_display(a["weeks"]),
            "steps": [
                {"plan": "A", "action": "Submit", "journal": a["title"], "weeks": a["weeks"]},
            ]
        }

    # Realistic: rejected at A, accepted at B
    if a and b:
        total = a["weeks"] + REVISION_WEEKS + b["weeks"]
        scenarios["realistic"] = {
            "label":   "Realistic",
            "desc":    f"Rejected at A → accepted at {b['title'][:40]}{'...' if len(b['title']) > 40 else ''}",
            "weeks":   total,
            "display": weeks_to_display(total),
            "steps": [
                {"plan": "A", "action": "Submit",  "journal": a["title"], "weeks": a["weeks"]},
                {"plan": "",  "action": "Revise",  "journal": "Revise & reformat paper", "weeks": REVISION_WEEKS},
                {"plan": "B", "action": "Submit",  "journal": b["title"], "weeks": b["weeks"]},
            ]
        }

    # Worst case: rejected at A and B, accepted at C
    if a and b and c:
        total = a["weeks"] + REVISION_WEEKS + b["weeks"] + REVISION_WEEKS + c["weeks"]
        scenarios["worst_case"] = {
            "label":   "Worst Case",
            "desc":    f"Rejected at A and B → accepted at {c['title'][:40]}{'...' if len(c['title']) > 40 else ''}",
            "weeks":   total,
            "display": weeks_to_display(total),
            "steps": [
                {"plan": "A", "action": "Submit",  "journal": a["title"], "weeks": a["weeks"]},
                {"plan": "",  "action": "Revise",  "journal": "Revise & reformat paper", "weeks": REVISION_WEEKS},
                {"plan": "B", "action": "Submit",  "journal": b["title"], "weeks": b["weeks"]},
                {"plan": "",  "action": "Revise",  "journal": "Revise & reformat paper", "weeks": REVISION_WEEKS},
                {"plan": "C", "action": "Submit",  "journal": c["title"], "weeks": c["weeks"]},
            ]
        }

    # ── Advice ────────────────────────────────────────────────────────────
    if a and b:
        opt_w = scenarios.get("optimistic", {}).get("weeks", 0)
        real_w = scenarios.get("realistic", {}).get("weeks", 0)
        advice = (
            f"Start with Plan A. If accepted, you'll be published in {weeks_to_display(opt_w)}. "
            f"If rejected, expect the full process to take {weeks_to_display(real_w)} through Plan B. "
            f"Use the rejection feedback to strengthen your paper before resubmitting."
        )
    elif a:
        advice = f"Submit to Plan A. Expected review time: {a['display']}."
    else:
        advice = "No timeline available — no journals found."

    return {
        "per_plan":  per_plan,
        "scenarios": scenarios,
        "advice":    advice,
    }
