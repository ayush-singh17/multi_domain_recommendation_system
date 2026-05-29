"""
STEP 4 — Risk Assessment
Journal Recommendation System

What this script does:
  - Takes the top candidate journals from Step 3
  - Scores each journal across 5 risk dimensions
  - Produces a risk_score (0–100) and risk_level (Low / Medium / High)
  - Journals with high risk are flagged before ranking

Risk Dimensions:
  1. Citation Impact   — SJR and Citations/Doc
  2. Academic Standing — H-index
  3. Longevity         — how many years the journal has been indexed
  4. Publisher Trust   — known reputable publishers vs unknown
  5. Domain Match      — does the journal's area match the abstract's domain?
"""

import pandas as pd
import pickle
import re
from step3b_bert_rerank import tokenize


# ── Trusted publisher list (based on dataset's top publishers) ────────────────
TRUSTED_PUBLISHERS = {
    "elsevier", "springer", "wiley", "taylor", "francis", "sage", "oxford",
    "cambridge", "nature", "ieee", "acm", "aps", "bmc", "hindawi", "karger",
    "thieme", "lippincott", "wolters", "kluwer", "biomed", "frontiers",
    "pubmed", "royal", "american", "national", "lancet", "bmj", "cell",
    "plos", "mdpi", "walter", "gruyter", "brill", "emerald", "informa",
    "de gruyter", "massachusetts", "rutgers", "johns hopkins", "mit press"
}


def publisher_is_trusted(publisher: str) -> bool:
    pub = publisher.lower()
    return any(keyword in pub for keyword in TRUSTED_PUBLISHERS)


def coverage_years(coverage: str) -> int:
    """Extract number of years a journal has been indexed from Coverage field."""
    years = re.findall(r"\d{4}", str(coverage))
    if len(years) >= 2:
        return int(years[-1]) - int(years[0])
    return 0


# ── Domain keyword mapping ───────────────────────────────────────────────────
# Maps abstract keywords → dataset Areas they signal
# Covers all 27 Areas in the dataset
DOMAIN_SIGNALS = {
    "Medicine": {
        "clinical", "patient", "disease", "diagnosis", "treatment", "hospital",
        "surgery", "therapy", "medical", "cancer", "tumor", "drug", "radiology",
        "imaging", "pathology", "pharmaceutical", "vaccine", "infection", "viral",
        "bacterial", "symptom", "prognosis", "epidemiology", "pandemic", "covid",
        "retinal", "diabetic", "cardiac", "neural", "oncology", "genomic"
    },
    "Computer Science": {
        "algorithm", "neural", "network", "learning", "classification", "detection",
        "convolutional", "transformer", "language", "vision", "recognition", "nlp",
        "robot", "autonomous", "compiler", "database", "distributed", "cloud",
        "encryption", "cybersecurity", "software", "hardware", "computing",
        "artificial", "intelligence", "deep", "reinforcement", "generative"
    },
    "Arts and Humanities": {
        "ethics", "philosophy", "moral", "justice", "rights", "fairness",
        "accountability", "bias", "discrimination", "society", "culture",
        "history", "literature", "language", "rhetoric", "narrative", "aesthetic",
        "epistemology", "ontology", "logic", "consciousness", "identity"
    },
    "Social Sciences": {
        "social", "policy", "governance", "regulation", "law", "legal",
        "political", "economic", "behavioral", "psychological", "sociological",
        "inequality", "privacy", "consent", "autonomy", "transparency",
        "accountability", "democracy", "institution", "community", "welfare"
    },
    "Mathematics": {
        "theorem", "proof", "convergence", "optimization", "probabilistic",
        "statistical", "bayesian", "stochastic", "differential", "algebraic",
        "topology", "geometry", "graph", "combinatorial", "numerical"
    },
    "Engineering": {
        "system", "design", "control", "signal", "sensor", "embedded",
        "mechanical", "electrical", "structural", "manufacturing", "automation",
        "robotic", "aerospace", "civil", "industrial", "thermal", "fluid"
    },
    "Environmental Science": {
        "climate", "carbon", "emission", "biodiversity", "ecosystem",
        "pollution", "sustainability", "renewable", "coral", "ocean",
        "atmosphere", "species", "conservation", "deforestation", "habitat"
    },
    "Physics and Astronomy": {
        "quantum", "particle", "photon", "laser", "magnetic", "gravitational",
        "spectroscopy", "telescope", "cosmological", "nuclear", "plasma",
        "electromagnetic", "thermodynamic", "optical", "astrophysical"
    },
    "Economics. Econometrics and Finance": {
        "market", "price", "auction", "equilibrium", "mechanism", "fiscal",
        "monetary", "trade", "investment", "portfolio", "volatility",
        "econometric", "regression", "elasticity", "welfare", "procurement"
    },
    "Psychology": {
        "cognitive", "behavior", "emotion", "mental", "anxiety", "depression",
        "perception", "memory", "attention", "motivation", "personality",
        "therapy", "neuroscience", "developmental", "stress", "trauma"
    },
    "Biochemistry. Genetics and Molecular Biology": {
        "protein", "gene", "dna", "rna", "sequence", "mutation", "chromosome",
        "enzyme", "cell", "molecular", "expression", "pathway", "metabolic",
        "genomic", "proteomics", "transcription", "synthesis", "biological"
    },
    "Neuroscience": {
        "brain", "neuron", "cortex", "synapse", "cognitive", "neural",
        "plasticity", "memory", "perception", "consciousness", "dopamine",
        "serotonin", "hippocampus", "prefrontal", "neurological", "spine"
    },
    "Multidisciplinary": {
        "interdisciplinary", "cross", "multi", "convergence", "intersection",
        "transdisciplinary", "integrated", "hybrid", "combined", "complex"
    },
}


def detect_abstract_domains(abstract_tokens: list) -> set:
    """
    Detects which dataset Areas are signalled by the abstract tokens.
    Returns a set of area names (e.g. {'Medicine', 'Computer Science'}).
    An abstract can belong to multiple domains simultaneously.
    """
    detected = set()
    token_set = set(abstract_tokens)
    for area, keywords in DOMAIN_SIGNALS.items():
        if token_set & keywords:          # any overlap → domain detected
            detected.add(area)
    return detected


def domain_match_score(abstract_tokens: list, journal_areas: str) -> float:
    """
    Cross-domain aware domain match.

    Logic:
    1. Detect all domains present in the abstract
    2. Check if the journal's Areas overlap with ANY detected domain
    3. For interdisciplinary abstracts (2+ domains), be more lenient:
       matching even one domain counts as a good match

    Returns a score 0.0–1.0.
    """
    detected_domains = detect_abstract_domains(abstract_tokens)
    journal_area_set = set(a.strip() for a in str(journal_areas).split(","))

    if not detected_domains:
        # Fallback: simple token overlap (for very short abstracts)
        areas_tokens = set(re.findall(r"[a-z]+", str(journal_areas).lower()))
        matches = sum(1 for t in abstract_tokens if t in areas_tokens)
        return min(matches / max(len(abstract_tokens), 1), 1.0)

    # How many detected domains does this journal cover?
    matching_domains = detected_domains & journal_area_set

    if not matching_domains:
        # Check partial string match for cases like
        # "Economics. Econometrics and Finance" vs "Economics"
        for jarea in journal_area_set:
            for darea in detected_domains:
                if any(word in jarea for word in darea.split()[:2]):
                    matching_domains.add(darea)
                    break

    if not matching_domains:
        return 0.0

    # Score: fraction of detected domains covered by this journal
    # Interdisciplinary papers get credit for partial coverage
    return len(matching_domains) / len(detected_domains)


def compute_risk(row: pd.Series, abstract_tokens: list[str]) -> dict:
    """
    Computes a risk score for a single journal.

    Scoring logic (lower penalty = safer journal):
      - Each dimension contributes 0–20 penalty points
      - Total risk_score = sum of penalties (0 = safest, 100 = riskiest)
    """
    penalties = {}

    # ── 1. Citation Impact (SJR) ──────────────────────────────────────────
    sjr = float(row["SJR"])
    if sjr == 0:
        penalties["sjr"] = 20        # no SJR data → high risk
    elif sjr < 0.177:
        penalties["sjr"] = 15        # bottom 25%
    elif sjr < 0.356:
        penalties["sjr"] = 10        # 25–50th percentile
    elif sjr < 0.745:
        penalties["sjr"] = 5         # 50–75th percentile
    else:
        penalties["sjr"] = 0         # top 25%

    # ── 2. H-index ────────────────────────────────────────────────────────
    h = int(row["H_index"])
    if h < 5:
        penalties["h_index"] = 20
    elif h < 10:
        penalties["h_index"] = 15
    elif h < 25:
        penalties["h_index"] = 10
    elif h < 58:
        penalties["h_index"] = 5
    else:
        penalties["h_index"] = 0

    # ── 3. Longevity (Coverage years) ────────────────────────────────────
    years = coverage_years(row["Coverage"])
    if years < 3:
        penalties["longevity"] = 20   # very new or barely indexed
    elif years < 8:
        penalties["longevity"] = 15
    elif years < 17:
        penalties["longevity"] = 10
    elif years < 34:
        penalties["longevity"] = 5
    else:
        penalties["longevity"] = 0

    # ── 4. Publisher Trust ────────────────────────────────────────────────
    if row["Publisher"] == "Unknown Publisher":
        penalties["publisher"] = 20
    elif publisher_is_trusted(row["Publisher"]):
        penalties["publisher"] = 0
    else:
        penalties["publisher"] = 10   # known but not top-tier

    # ── 5. Domain Match ───────────────────────────────────────────────────
    dm = domain_match_score(abstract_tokens, row["Areas"])
    if dm == 0:
        penalties["domain"] = 20
    elif dm < 0.05:
        penalties["domain"] = 10
    else:
        penalties["domain"] = 0

    risk_score = sum(penalties.values())

    if risk_score <= 20:
        risk_level = "Low"
    elif risk_score <= 50:
        risk_level = "Medium"
    else:
        risk_level = "High"

    return {
        "risk_score":       risk_score,
        "risk_level":       risk_level,
        "penalty_sjr":      penalties["sjr"],
        "penalty_h_index":  penalties["h_index"],
        "penalty_longevity":penalties["longevity"],
        "penalty_publisher":penalties["publisher"],
        "penalty_domain":   penalties["domain"],
    }



def compute_predatory_score(row: pd.Series) -> dict:
    """
    Computes a predatory journal risk score from 0-100.
    Uses only signals available in our dataset.

    Signals and weights:
      - Review time paradox    : weeks < 2 AND sjr < 0.2  → +40
      - Old but no citations   : coverage > 5 yrs AND h < 5 → +30
      - Not indexed anywhere   : not in DOAJ AND sjr == 0  → +25
      - Pay-to-publish suspect : apc > 0 AND h < 10        → +20
      - Unknown publisher      : publisher unverifiable     → +15
      - Brand new unproven     : coverage < 3 yrs AND sjr == 0 → +10

    Score >= 60 → Potentially Predatory (shown as warning)
    Score 30-59 → Caution
    Score < 30  → No flag
    """
    score  = 0
    flags  = []

    sjr        = float(row.get("SJR", 0) or 0)
    h_index    = int(row.get("H_index", 0) or 0)
    in_doaj    = bool(row.get("in_doaj", False))
    publisher  = str(row.get("Publisher", ""))
    apc_usd    = row.get("apc_usd")
    weeks      = row.get("weeks_to_publish")
    cov_years  = coverage_years(str(row.get("Coverage", "")))

    # ── Signal 1: Review time paradox ────────────────────────────────────
    try:
        w = float(weeks) if weeks is not None else None
    except:
        w = None

    if w is not None and w < 2 and sjr < 0.2:
        score += 40
        flags.append("⚠ Suspiciously fast review time (<2 weeks) for a low-ranked journal")

    # ── Signal 2: Old journal but no academic standing ───────────────────
    if cov_years > 5 and h_index < 5:
        score += 30
        flags.append("⚠ Journal has been running 5+ years but H-index remains below 5")

    # ── Signal 3: Not indexed in DOAJ or Scopus ───────────────────────────
    if not in_doaj and sjr == 0:
        score += 25
        flags.append("⚠ Not indexed in DOAJ and has no Scopus/SJR record")

    # ── Signal 4: Charges APC but lacks academic standing ────────────────
    try:
        apc_val = float(apc_usd) if apc_usd is not None else 0
    except:
        apc_val = 0

    if apc_val > 0 and h_index < 10:
        score += 20
        flags.append("⚠ Charges APC fees but H-index is below 10")

    # ── Signal 5: Unknown or unverifiable publisher ───────────────────────
    if publisher == "Unknown Publisher" or not publisher_is_trusted(publisher):
        if sjr < 0.1 and h_index < 5:
            score += 15
            flags.append("⚠ Publisher is not in recognised publisher list")

    # ── Signal 6: Very new with no standing ──────────────────────────────
    if cov_years < 3 and sjr == 0 and h_index < 3:
        score += 10
        flags.append("⚠ Newly indexed journal with no citation record yet")

    # Cap at 100
    score = min(score, 100)

    if score >= 60:
        level = "Potentially Predatory"
    elif score >= 30:
        level = "Caution"
    else:
        level = "Clear"

    return {
        "predatory_score": score,
        "predatory_level": level,
        "predatory_flags": flags,
    }


def assess_risk(results: pd.DataFrame, abstract: str) -> pd.DataFrame:
    """
    Applies risk scoring to all candidate journals.
    Returns the dataframe with risk columns added.
    """
    abstract_tokens = tokenize(abstract)
    risk_rows      = results.apply(lambda row: compute_risk(row, abstract_tokens), axis=1)
    predatory_rows = results.apply(lambda row: compute_predatory_score(row), axis=1)
    risk_df        = pd.DataFrame(risk_rows.tolist())
    predatory_df   = pd.DataFrame(predatory_rows.tolist())
    combined       = pd.concat([results.reset_index(drop=True), risk_df, predatory_df], axis=1)
    return combined


def display_risk_results(results: pd.DataFrame):
    print(f"\n{'#':<3} {'Risk':<8} {'Score':<7} {'BM25':<8} {'Q':<5} {'Title'}")
    print("-" * 90)
    for i, row in results.iterrows():
        flag = "⚠" if row["risk_level"] == "High" else ("~" if row["risk_level"] == "Medium" else "✓")
        print(f"{i+1:<3} {flag} {row['risk_level']:<6} {row['risk_score']:<7} "
              f"{row['bm25_score']:<8} {row['Quartile']:<5} {row['Title']}")
        print(f"    Publisher: {row['Publisher']}  |  H-index: {row['H_index']}  "
              f"|  SJR: {row['SJR']}  |  Areas: {row['Areas']}")
        print()


def main():
    print("\n=== STEP 4: Risk Assessment ===\n")

    index, df = load_resources()

    abstracts = [
        {
            "label": "Medical AI / Diabetic Retinopathy",
            "text": """
                This paper proposes a deep learning framework for early detection of diabetic
                retinopathy using convolutional neural networks. We analyze retinal fundus images
                and classify severity levels using transfer learning on ResNet50. The model
                achieves 94% accuracy on the APTOS dataset and outperforms existing methods
                in sensitivity and specificity.
            """
        },
        {
            "label": "Economics / Game Theory",
            "text": """
                We examine Nash equilibrium strategies in multi-player auction mechanisms.
                Using mechanism design theory, we derive conditions under which truthful
                bidding constitutes a dominant strategy equilibrium. Applications to
                spectrum auctions and public goods procurement are discussed.
            """
        },
    ]

    for abstract in abstracts:
        print(f"\n{'='*90}")
        print(f"ABSTRACT: {abstract['label']}")
        print(f"{'='*90}")

        candidates = search(abstract["text"], index, df, top_n=10)
        results    = assess_risk(candidates, abstract["text"])
        display_risk_results(results)

        low    = (results["risk_level"] == "Low").sum()
        medium = (results["risk_level"] == "Medium").sum()
        high   = (results["risk_level"] == "High").sum()
        print(f"  Risk summary → Low: {low}  Medium: {medium}  High: {high}")

    print("\n✓ Step 4 complete. Run step5_ranking.py next.\n")


if __name__ == "__main__":
    main()
