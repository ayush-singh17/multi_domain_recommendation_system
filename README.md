# JournalFinder — AI-Powered Academic Journal Recommendation System

> A hybrid NLP recommendation engine that helps researchers find the right journal for their work — combining BM25 sparse retrieval, SPECTER2 dense embeddings, and a multi-factor scoring formula to surface the most relevant, safe, and impactful publication venues.

---

## What Problem Does This Solve?

Choosing where to submit academic research is one of the most consequential and time-consuming decisions a researcher makes. The wrong journal means rejection, wasted months, or worse — predatory publication.

JournalFinder takes a research abstract and returns three strategic plans:

- **Plan A (Ambitious)** — Top Q1 journals with high impact, matched by meaning
- **Plan B (Balanced)** — Solid Q2 journals balancing prestige and acceptance rate
- **Plan C (Safe)** — High-relevance, low-risk journals for reliable publication

Each recommendation includes a risk assessment, historical trend charts, submission timeline estimates, and plain-English explanations of why each journal was chosen.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  React SPA (Frontend)                       │
│         Framer Motion · TailwindCSS · Recharts              │
└──────────────────────┬──────────────────────────────────────┘
                       │ JWT-authenticated REST API
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Django REST API (API Gateway)                  │
│     SimpleJWT · Search Logging · SavedJournals · Feedback   │
└──────────────────────┬──────────────────────────────────────┘
                       │ Internal HTTP (requests.post)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│             FastAPI ML Service (Computation Engine)         │
│                                                             │
│  BM25 Sparse Retrieval → SPECTER2 Dense Reranking           │
│  → Risk Assessment → Weighted Scoring → Strategy Split      │
│  → Explainability Layer → PDF Generation                    │
│  │                                                           │
│  Assets loaded ONCE at startup:                             │
│  bm25_index.pkl · journal_embeddings.npy · trends.csv       │
└─────────────────────────────────────────────────────────────┘
```

**Design rationale:** Django handles auth, state, and logging. FastAPI handles ML inference. This separation means heavy matrix operations never block the web server, and each service can be scaled independently.

---

## The Recommendation Pipeline — Step by Step

When a user submits an abstract, here is exactly what happens:

### Step 1 — Input Normalisation
If the user searches by keywords instead of abstract, `keywords_to_abstract()` expands them into a fluent pseudo-academic sentence. This dramatically improves embedding quality compared to passing raw comma-separated terms to a sentence transformer.

```python
# "machine learning, NLP" →
# "This paper investigates machine learning and natural language 
#  processing with applications in text classification..."
```

### Step 2 — Sparse Retrieval (BM25)
The abstract is tokenized and queried against a pre-built BM25 index (`bm25_index.pkl`) covering 29,000+ indexed journals. BM25 finds candidates with strong exact keyword overlap — fast, interpretable, no GPU required.

### Step 3 — Dense Reranking (SPECTER2)
The abstract is embedded using `sentence-transformers` (SPECTER2 — trained specifically on academic text). Cosine similarity between the abstract vector and pre-computed `journal_embeddings.npy` reorders the BM25 candidates by **semantic meaning**, not just keyword frequency.

```
Hybrid score = α × BM25_score + (1-α) × cosine_similarity
```

### Step 4 — Risk Assessment
Each candidate journal is scrutinised across multiple signals:

| Signal | Weight |
|---|---|
| H-index | High |
| SJR score | High |
| Citations per document | Medium |
| Publisher trust (TRUSTED_PUBLISHERS set) | High |
| Domain alignment with abstract | Medium |

Risk level assigned: **Low / Medium / High**

### Step 5 — Weighted Final Scoring
A multi-factor formula ranks the final candidates using fixed weights to ensure a balanced recommendation:

`Final Score = (0.50 × Relevance) + (0.30 × Safety) + (0.20 × Citation Impact)`

### Step 6 — Strategic Split
The ranked list is divided into three plans:
- **Plan A** — Top Q1 journals, Low risk
- **Plan B** — Solid Q2 journals, Medium risk acceptable
- **Plan C** — Best remaining by relevance, safest risk profile

### Step 7 — Explainability
The pipeline generates plain-English explanations for every recommendation:

> *"Recommended because it matches your keywords 'machine learning' and 'NLP', has a Low risk profile, and a strong H-index of 45 with consistent citation growth over 5 years."*

### Step 8 — Data Enrichment
Each result is enriched with:
- Historical impact factor trends (from `journal_trends.csv`)
- Estimated submission → peer review → publication timeline
- Matching token highlights from the abstract

---

## Features

### Search
- **Abstract mode** — paste full research abstract for semantic search
- **Keyword mode** — pill-style keyword input auto-expanded to pseudo-abstract

### Results Dashboard
- Plan A / B / C journal cards with risk badges and quartile labels
- Matching keyword highlights per journal
- Side-by-side journal comparison modal
- 5-year impact factor trend charts (Recharts)
- Submission-to-publication timeline visualisation
- One-click PDF report download (generated server-side with ReportLab)

### User Features
- JWT authentication (register, login, refresh)
- Search history with full result replay
- Save journals with personal notes
- Feedback / bug report submission

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, TailwindCSS, Framer Motion, Recharts |
| Backend | Django, Django REST Framework |
| Authentication | djangorestframework-simplejwt (JWT) |
| ML Service | FastAPI, Uvicorn |
| Sparse Retrieval | BM25 (rank-bm25) |
| Dense Retrieval | sentence-transformers (SPECTER2) |
| PDF Generation | ReportLab, Pillow |
| Database | MySQL |
| HTTP Client | axios (frontend), requests (Django→FastAPI) |

---

## ML Assets

| Asset | Description |
|---|---|
| `bm25_index.pkl` | Pre-built BM25 index over 29,000+ journals |
| `journal_embeddings.npy` | Pre-computed SPECTER2 embeddings for all journals |
| `journal_trends.csv` | 5-year historical impact factor data per journal |
| `trusted_publishers.json` | Curated list of verified non-predatory publishers |

All assets are loaded **once at FastAPI startup** and kept in memory — no reloading per request, sub-second inference after warmup.

---

## Database Schema

```
users
  id · email · name · institution · is_active · is_staff

searches  
  id · user→users · abstract · focus · search_mode
  keywords · results_json · created_at

saved_journals
  id · user→users · search→searches · issn · journal_name
  quartile · h_index · notes · saved_at

feedback
  id · user→users · type · message · created_at
```

---

## API Endpoints

### Django REST API

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login, returns JWT access + refresh |
| POST | `/api/auth/token/refresh/` | Refresh JWT access token |
| POST | `/api/search/recommend/` | Main recommendation endpoint |
| GET | `/api/search/history/` | User's past searches |
| POST | `/api/search/save-journal/` | Save a journal to bookmarks |
| GET | `/api/search/saved/` | List saved journals |
| POST | `/api/feedback/` | Submit feedback or bug report |

### FastAPI ML Service (Internal)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/recommend` | Full pipeline — returns ranked plans |
| POST | `/pdf` | Same pipeline — returns PDF download stream |
| GET | `/health` | Service health check |

---

## Local Setup

### Prerequisites
- Python 3.10+
- Node 18+
- MySQL

### 1. Clone
```bash
git clone https://github.com/yourname/journalfinder
cd journalfinder
```

### 2. Django Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # configure DB credentials and ML_URL
python manage.py migrate
python manage.py runserver 8000
```

### 3. FastAPI ML Service
```bash
cd ml_service
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

> Note: First startup takes 30-60 seconds while assets load into memory. Subsequent requests are sub-second.

### 4. Frontend
```bash
cd frontend
npm install
cp .env.example .env  # set REACT_APP_API_URL
npm start
```

### Environment Variables

**backend/.env**
```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DB_NAME=journalfinder
DB_USER=root
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=3306
ML_URL=http://localhost:8001
```

---

## Project Structure

```
journalfinder/
├── frontend/
│   └── src/
│       ├── pages/               # React screens (Search, Results, History)
│       └── components/          # UI components (JournalCard, TrendChart, etc.)
├── backend/
│   ├── users/                   # Custom User model, JWT auth
│   └── searches/                # Search history, SavedJournal models
├── ml_service/
│   ├── main.py                  # FastAPI app (wraps the pipeline)
│   └── requirements.txt
├── step1_prepare_data.py        # Pipeline: Data cleaning
├── step2_build_index.py         # Pipeline: BM25 index generation
├── step2b_build_bert_index.py   # Pipeline: SPECTER2 embedding generation
├── step3_query.py               # Pipeline: Candidate retrieval
├── step4_risk_assessment.py     # Pipeline: 5-factor risk scoring
├── step5_ranking.py             # Pipeline: Final hybrid scoring
├── step6_strategy.py            # Pipeline: Plan A/B/C assignment
├── step7_explain.py             # Pipeline: Dynamic NLP explanations
├── bm25_index.pkl               # Asset: Sparse index
├── journal_embeddings.npy       # Asset: Dense embeddings
└── journal_trends.csv           # Asset: Historical impact factor data
```

---

## Why Hybrid Retrieval?

BM25 alone misses semantic similarity — "cardiac arrest" and "heart failure" score low despite meaning the same thing. Dense embeddings alone miss exact technical terms that matter in academic search.

The hybrid approach combines both:

```
BM25      → fast, keyword-exact, interpretable
SPECTER2  → semantic, meaning-aware, domain-specific (trained on academic papers)
Combined  → best of both: exact match + conceptual relevance
```

SPECTER2 is specifically chosen over general-purpose models (e.g., all-MiniLM) because it was pre-trained on citation graphs and paper abstracts — making it significantly more accurate for academic domain matching.

---

## PDF Report

The `/pdf` endpoint runs the full recommendation pipeline and streams a dynamically generated PDF including:
- All three plans with journal details
- Risk assessments and scoring breakdown
- Trend charts embedded as images (Pillow)
- Personalised recommendation explanations

Generated server-side with ReportLab — no client-side rendering required.

*Built as part of a supervised research project — July 2026*
