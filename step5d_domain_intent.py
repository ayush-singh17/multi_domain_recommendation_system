"""
step5d_domain_intent.py
Domain Intent Classification + Primary Domain Weighting

Problem this solves:
  SCImago assigns journals multiple categories (e.g. Computer Science + Medicine)
  without weighting which domain is PRIMARY.

  This causes method-primary CS journals to rank above application-specific
  medical/environmental journals for application-driven abstracts.

  Example:
    Abstract: "BiLSTM for diabetes prediction in patients"
    WRONG #1:  International Journal of Neural Systems  (CS-primary)
    CORRECT #1: Diabetes Care / npj Digital Medicine    (medicine-primary)

Version 2 improvements over V1:
  - Uses BOTH title AND areas for journal domain classification
  - Handles vague/general titles (Sensors, IEEE Access, Scientific Reports)
  - Uses area_count weighted scoring for hybrid detection
  - Better hybrid journal handling (Applied AI journals get light penalty)
"""

import re

# ── Abstract intent signals ───────────────────────────────────────────────────

APPLICATION_SIGNALS = {

    "medical_clinical": [
        "patient", "patients", "clinical", "disease", "diagnosis", "treatment",
        "therapy", "symptoms", "prognosis", "survival", "mortality", "morbidity",
        "hospital", "ehr", "electronic health", "medical record", "cohort",
        "randomized", "trial", "outcome", "comorbidity", "biomarker",
        "diabetes", "diabetic", "cancer", "tumor", "cardiovascular", "cardiac",
        "retinopathy", "alzheimer", "parkinson", "depression", "hypertension",
        "covid", "sepsis", "stroke", "obesity", "epilepsy", "pneumonia",
        "healthcare", "physician", "nurse", "surgery", "radiology", "pathology",
        "biopsy", "imaging", "screening", "prevention", "drug", "medication",
        "dosage", "pharmacology", "genomics", "precision medicine",
    ],

    "environmental": [
        "ecosystem", "biodiversity", "climate", "pollution", "carbon", "emission",
        "deforestation", "species", "habitat", "conservation", "soil", "water quality",
        "ocean", "coral", "drought", "flood", "sustainability", "renewable",
        "greenhouse", "atmospheric", "sediment", "watershed",
    ],

    "legal_policy": [
        "legislation", "regulation", "policy", "law", "legal", "court", "governance",
        "compliance", "rights", "ethics", "privacy", "jurisdiction", "statute",
        "enforcement", "constitution", "treaty", "litigation",
    ],

    "economics_finance": [
        "gdp", "inflation", "monetary", "fiscal", "market", "stock", "bond",
        "investment", "portfolio", "bank", "financial", "economic growth",
        "poverty", "inequality", "trade", "tariff", "supply chain",
        "consumer", "household", "employment", "labour", "wage",
    ],

    "education": [
        "student", "teacher", "curriculum", "learning outcome", "pedagogy",
        "classroom", "school", "university", "assessment", "literacy",
        "higher education", "e-learning", "instruction", "academic performance",
    ],

    "social_science": [
        "survey", "interview", "qualitative", "ethnography", "demographic",
        "population", "community", "social", "culture", "behaviour", "attitude",
        "perception", "gender", "race", "ethnicity", "inequality", "welfare",
    ],
}

METHOD_SIGNALS = [
    "neural architecture", "attention mechanism", "transformer architecture",
    "backpropagation", "gradient descent", "convolutional layer", "pooling layer",
    "activation function", "hyperparameter", "loss function", "epoch",
    "benchmark dataset", "imagenet", "coco dataset", "cifar",
    "ablation study", "state of the art", "baseline comparison",
    "time complexity", "space complexity", "np-hard", "polynomial time",
    "algorithm design", "graph theory", "automata", "compiler",
]

MODALITY_SIGNALS = {
    "imaging": [
        "image", "imaging", "ct", "mri", "x-ray", "radiomics",
        "segmentation", "scan", "ultrasound", "tomography"
    ],
    "genomics": [
        "gene", "genomic", "rna", "dna", "sequence",
        "expression", "transcriptomic"
    ],
    "clinical_data": [
        "ehr", "patient data", "vital signs", "lab results"
    ]
}

# ── Journal classification signals ───────────────────────────────────────────

# Title words that strongly indicate a METHODS/TECHNIQUE primary journal
JOURNAL_METHOD_TITLE_SIGNALS = [
    "neural network", "neural systems", "machine learning", "artificial intelligence",
    "deep learning", "pattern recognition", "computer vision", "natural language",
    "data mining", "information retrieval", "knowledge-based", "expert systems",
    "computational intelligence", "fuzzy", "genetic algorithm", "evolutionary",
    "signal processing", "image processing", "robotics", "automation",
    "soft computing", "swarm intelligence",
]

# Title words that indicate APPLICATION-primary in a domain
JOURNAL_APPLICATION_TITLE_SIGNALS = {
    "medical_clinical": [
        "medicine", "medical", "health", "clinical", "disease", "patient",
        "healthcare", "hospital", "nursing", "therapy", "pharmacology",
        "oncology", "cardiology", "neurology", "diabetes", "radiology",
        "surgery", "pediatric", "geriatric", "psychiatry", "epidemiology",
        "biomarker", "genomics", "public health",
    ],
    "environmental": [
        "environment", "ecology", "conservation", "sustainability", "climate",
        "pollution", "biodiversity", "earth", "ocean", "atmosphere", "soil",
    ],
    "legal_policy": [
        "law", "legal", "policy", "governance", "regulation", "rights", "justice",
    ],
    "economics_finance": [
        "economics", "finance", "banking", "monetary", "trade", "business",
        "management", "accounting",
    ],
    "education": [
        "education", "learning", "teaching", "curriculum", "pedagogy", "school",
        "university", "academic",
    ],
}

# Areas (SCImago categories) that indicate METHOD-primary domain
METHOD_AREAS = [
    "computer science",
    "mathematics",
    "engineering",
]

# Areas that indicate APPLICATION-primary in a domain
APPLICATION_AREAS = {
    "medical_clinical":   ["medicine", "health professions", "nursing", "pharmacology"],
    "environmental":      ["environmental science", "earth and planetary sciences", "agricultural"],
    "legal_policy":       ["social sciences", "arts and humanities"],
    "economics_finance":  ["economics, econometrics and finance", "business, management"],
    "education":          ["social sciences"],
}

JOURNAL_MODALITY_SIGNALS = {
    "imaging": [
        "imaging", "image", "radiology", "tomography",
        "medical image", "radiomics", "ultrasound", "mri", "ct"
    ],
    "genomics": [
        "genomic", "gene", "bioinformatics", "computational biology",
        "transcriptomic", "molecular", "rna", "dna"
    ],
    "clinical_data": [
        "informatics", "digital health"
    ]
}

# Journals that are KNOWN to be general/multidisciplinary — do not penalise
GENERAL_JOURNALS = {
    "scientific reports", "plos one", "plos biology", "nature communications",
    "ieee access", "frontiers in", "heliyon", "f1000research", "royal society open science",
    "cureus", "mdpi", "sustainability",
}


def classify_abstract_intent(abstract: str) -> dict:
    """
    Classifies the primary intent of an abstract.
    Returns primary domain, whether it is application-driven, and domain scores.
    """
    text     = abstract.lower()
    domain_scores = {}
    for domain, signals in APPLICATION_SIGNALS.items():
        score = sum(
            (2 if " " in sig else 1)
            for sig in signals
            if sig in text
        )
        domain_scores[domain] = score

    method_score = sum(1 for sig in METHOD_SIGNALS if sig in text)

    modality_scores = {}
    for mod, signals in MODALITY_SIGNALS.items():
        score = sum(1 for sig in signals if sig in text)
        if score > 0:
            modality_scores[mod] = score
    
    abstract_modality = None
    if modality_scores:
        abstract_modality = max(modality_scores, key=modality_scores.get)

    if domain_scores:
        primary_domain = max(domain_scores, key=domain_scores.get)
        primary_score  = domain_scores[primary_domain]
    else:
        primary_domain = "general"
        primary_score  = 0

    is_application_driven = (primary_score >= 2) and (primary_score >= method_score)

    return {
        "primary_domain":        primary_domain,
        "primary_score":         primary_score,
        "is_application_driven": is_application_driven,
        "domain_scores":         domain_scores,
        "method_score":          method_score,
        "abstract_modality":     abstract_modality,
    }


def classify_journal_domain(title: str, areas: str) -> dict:
    """
    V2 — Uses BOTH title AND areas for journal domain classification.

    Scoring approach:
    - Title method signals:      strong evidence of method-primary (+3 each)
    - Title application signals: strong evidence of application domain (+3 each)
    - Areas method signals:      supporting evidence of method-primary (+1 each)
    - Areas application signals: supporting evidence of application domain (+1 each)

    Returns method_score, application_score, primary classification.
    """
    title_lower = str(title).lower()
    areas_lower = str(areas).lower()

    # Check if journal is a known general/multidisciplinary journal
    is_general = any(g in title_lower for g in GENERAL_JOURNALS)

    # ── Title-based scoring ───────────────────────────────────────────────────
    method_score = sum(
        3 for sig in JOURNAL_METHOD_TITLE_SIGNALS if sig in title_lower
    )

    application_domain = None
    application_score  = 0
    for domain, signals in JOURNAL_APPLICATION_TITLE_SIGNALS.items():
        score = sum(3 for sig in signals if sig in title_lower)
        if score > application_score:
            application_score  = score
            application_domain = domain if score > 0 else None

    # ── Modality detection ────────────────────────────────────────────────────
    journal_modality = None
    for mod, signals in JOURNAL_MODALITY_SIGNALS.items():
        if any(sig in title_lower for sig in signals):
            journal_modality = mod
            break

    # ── Areas-based scoring ───────────────────────────────────────────────────
    # Count how many of the journal's areas are method-primary
    method_area_score = sum(
        1 for area in METHOD_AREAS if area in areas_lower
    )

    # Count how many of the journal's areas match application domains
    best_app_area_domain = None
    best_app_area_score  = 0
    for domain, area_signals in APPLICATION_AREAS.items():
        score = sum(1 for sig in area_signals if sig in areas_lower)
        if score > best_app_area_score:
            best_app_area_score  = score
            best_app_area_domain = domain if score > 0 else None

    # Combine: title evidence is weighted 3x, areas evidence is 1x
    total_method_score = method_score + method_area_score
    total_app_score    = application_score + best_app_area_score

    # If title gave no signal, use areas as fallback
    if application_domain is None and best_app_area_domain:
        application_domain = best_app_area_domain

    # Primary classification
    is_method_primary = (
        total_method_score > total_app_score
        and total_method_score >= 3
        and not is_general
    )

    # Count areas for hybrid detection
    area_list  = [a.strip() for a in areas_lower.split(",") if a.strip()]
    area_count = len(area_list)
    is_hybrid  = (
        area_count >= 2
        and not is_general
        and (total_method_score > 0 or total_app_score > 0)
    )

    return {
        "is_method_primary":  is_method_primary,
        "is_general":         is_general,
        "application_domain": application_domain,
        "is_hybrid":          is_hybrid,
        "area_count":         area_count,
        "method_score":       total_method_score,
        "app_score":          total_app_score,
        "journal_modality":   journal_modality,
    }


def compute_intent_mismatch_penalty(
    abstract_intent: dict,
    journal_title:   str,
    journal_areas:   str,
) -> float:
    """
    Computes domain intent mismatch penalty (0.0 to 1.0).
    1.0 = no penalty. Lower = penalised.

    Penalty logic:
    Case 1: Journal is METHOD-primary, abstract is APPLICATION-driven
            → Strong penalty (0.55) if domains are unrelated
            → Mild penalty (0.90) if same domain but methods-first

    Case 2: Journal is HYBRID (method + application)
            → Check if application domain matches abstract domain
            → No penalty if they match (correct interdisciplinary journal)
            → Moderate penalty if they don't (wrong interdisciplinary fit)

    Case 3: Journal is GENERAL (PLOS ONE, Scientific Reports, IEEE Access)
            → No penalty — these legitimately publish anything

    Case 4: Abstract is METHOD-primary
            → No penalty applied at all (methods papers belong in methods journals)
    """
    # Never penalise if abstract is not clearly application-driven
    if not abstract_intent["is_application_driven"]:
        return 1.0

    if abstract_intent["primary_score"] < 2:
        return 1.0

    abstract_domain = abstract_intent["primary_domain"]
    abstract_modality = abstract_intent.get("abstract_modality")
    journal = classify_journal_domain(journal_title, journal_areas)

    # Never penalise general journals
    if journal["is_general"]:
        return 1.0

    # ── MODALITY AWARENESS ────────────────────────────────────────────────────
    # If both abstract and journal share the same modality, lightly boost it
    if abstract_modality and journal.get("journal_modality") == abstract_modality:
        return 1.08

    # ── Case 1: Clear method-primary journal ──────────────────────────────────
    if journal["is_method_primary"]:
        # IMPORTANT: for method-primary journals, only use title-derived app_domain
        # Areas-only application domain does NOT constitute genuine alignment
        # e.g. "International Journal of Neural Systems" has areas "CS, Medicine"
        # but its TITLE has zero medical vocabulary → it is NOT a clinical journal

        title_lower = str(journal_title).lower()

        # Check if title itself has application domain signals
        title_has_app_signal = False
        if journal["application_domain"]:
            domain_signals = JOURNAL_APPLICATION_TITLE_SIGNALS.get(
                journal["application_domain"], []
            )
            title_has_app_signal = any(sig in title_lower for sig in domain_signals)

        if not title_has_app_signal:
            # Title has no application signal — purely method-primary
            # Areas having "Medicine" is NOT sufficient to remove penalty
            if abstract_domain in ["medical_clinical", "environmental", "legal_policy"]:
                return 0.55   # strong penalty
            else:
                return 0.72   # moderate penalty

        if journal["application_domain"] == abstract_domain and title_has_app_signal:
            # Methods journal AND title confirms right application domain
            # e.g. "Medical Image Analysis" for a clinical AI paper
            return 0.88   # very light penalty

        # Methods journal, wrong application domain
        return 0.62

    # ── Case 2: Hybrid journal ────────────────────────────────────────────────
    if journal["is_hybrid"]:
        if journal["application_domain"] == abstract_domain:
            return 1.00   # hybrid journal that matches — perfect, no penalty
        elif journal["application_domain"] is None:
            return 0.85   # hybrid but unclear application alignment
        else:
            return 0.70   # hybrid but wrong application domain

    # ── Case 3: Application-primary journal ──────────────────────────────────
    # No penalty
    return 1.0


def apply_domain_intent_weighting(results, abstract: str):
    """
    Apply domain intent mismatch penalty to ranked results DataFrame.
    Called after normalisation in step5_ranking.rank().
    """
    import pandas as pd

    abstract_intent = classify_abstract_intent(abstract)

    if not abstract_intent["is_application_driven"]:
        results["intent_penalty"] = 1.0
        return results, abstract_intent

    penalties = []
    for _, row in results.iterrows():
        penalty = compute_intent_mismatch_penalty(
            abstract_intent,
            str(row.get("Title", "")),
            str(row.get("Areas", "")),
        )
        penalties.append(penalty)

    results = results.copy()
    results["domain_score"] = penalties

    penalised = sum(1 for p in penalties if p < 1.0)
    if penalised > 0:
        print(f"  Domain intent: penalised {penalised} journals  |  "
              f"abstract domain: {abstract_intent['primary_domain']} "
              f"(score: {abstract_intent['primary_score']})")

    return results, abstract_intent
