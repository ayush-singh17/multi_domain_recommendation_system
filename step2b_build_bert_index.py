"""
STEP 2b — Precompute BERT Embeddings (Offline)
Journal Recommendation System

What this script does:
  - Loads journals_clean.csv
  - Builds a bert_text field for each journal:
      Title + Categories (cleaned) + Areas
  - Encodes all 29,553 journals using SPECTER2
  - Saves embeddings to journal_embeddings.npy  (shape: 29553 × 768)
  - Saves bert_texts.pkl so we know which row maps to which journal

Run this ONCE. Takes ~5–15 minutes on GPU, ~30–60 min on CPU.
After this, runtime encoding is just the abstract (< 1 second).

Model: allenai/specter2
  - Trained specifically on scientific paper titles and abstracts
  - Far better than general BERT for academic text matching
  - 768-dimensional embeddings

Install requirements:
    pip install sentence-transformers numpy pandas
"""

import pandas as pd
import numpy as np
import pickle
import re
import time
import os


# ── Config ────────────────────────────────────────────────────────────────────
INPUT_FILE       = "journals_clean.csv"
EMBEDDINGS_FILE  = "journal_embeddings.npy"   # shape: (N, 768)
TEXTS_FILE       = "bert_texts.pkl"            # list of strings, same order as embeddings
MODEL_NAME       = "allenai/specter2_base"          # scientific text model
BATCH_SIZE       = 128                          # increase to 256 if you have >8GB VRAM
# ─────────────────────────────────────────────────────────────────────────────


def build_bert_text(row: pd.Series) -> str:
    """
    Constructs the text BERT will encode for each journal.
    Format: "Title. Categories. Areas"
    Quartile tags like (Q1) are stripped — BERT should match on topics, not rank.
    """
    cats = re.sub(r"\(Q\d\)", "", str(row["Categories"])).strip()
    cats = re.sub(r"\s+", " ", cats)
    return f"{row['Title']}. {cats}. {row['Areas']}"


def load_model():
    """Load SPECTER2 model. Downloads on first run (~400MB), cached after."""
    from sentence_transformers import SentenceTransformer

    print(f"  Loading model: {MODEL_NAME}")
    print(f"  (First run downloads ~400MB — cached after that)")

    model = SentenceTransformer(MODEL_NAME)

    # Move to GPU if available
    import torch
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"  GPU detected: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device("cpu")
        print(f"  No GPU found — using CPU (will be slower)")

    model = model.to(device)
    return model


def encode_journals(texts: list[str], model) -> np.ndarray:
    """
    Encodes all journal texts in batches.
    Returns numpy array of shape (N, 768).
    Shows progress every 10 batches.
    """
    total    = len(texts)
    all_embs = []
    start    = time.time()

    print(f"  Encoding {total:,} journals in batches of {BATCH_SIZE}...")
    print(f"  {'Batch':<8} {'Progress':<12} {'Elapsed':<12} {'ETA'}")
    print(f"  {'-'*50}")

    for i in range(0, total, BATCH_SIZE):
        batch     = texts[i : i + BATCH_SIZE]
        embeddings = model.encode(
            batch,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,   # L2 normalise → cosine sim = dot product
        )
        all_embs.append(embeddings)

        # Progress log every 10 batches
        batch_num = i // BATCH_SIZE + 1
        if batch_num % 10 == 0 or (i + BATCH_SIZE) >= total:
            done    = min(i + BATCH_SIZE, total)
            elapsed = time.time() - start
            rate    = done / elapsed
            eta     = (total - done) / rate if rate > 0 else 0
            pct     = done / total * 100
            print(f"  {batch_num:<8} {done:>6,}/{total:,} ({pct:.0f}%)  "
                  f"{elapsed:.0f}s elapsed    ETA: {eta:.0f}s")

    embeddings = np.vstack(all_embs)
    print(f"\n  Done. Shape: {embeddings.shape}  Total time: {time.time()-start:.0f}s")
    return embeddings


def save_outputs(embeddings: np.ndarray, texts: list[str]):
    """Save embeddings and texts to disk."""
    np.save(EMBEDDINGS_FILE, embeddings)
    print(f"  Saved embeddings → {EMBEDDINGS_FILE}  "
          f"({os.path.getsize(EMBEDDINGS_FILE)/1e6:.1f} MB)")

    with open(TEXTS_FILE, "wb") as f:
        pickle.dump(texts, f)
    print(f"  Saved texts      → {TEXTS_FILE}")


def verify(embeddings: np.ndarray, texts: list[str], model):
    """Quick smoke test — encode a test abstract and find top matches."""
    from sklearn.metrics.pairwise import cosine_similarity

    test_abstract = (
        "Deep learning model for detection of diabetic retinopathy "
        "using convolutional neural networks on retinal fundus images."
    )

    query_emb = model.encode(
        [test_abstract],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    # cosine similarity (embeddings are already L2-normalised so dot product works)
    scores  = (embeddings @ query_emb.T).squeeze()
    top_idx = np.argsort(scores)[::-1][:5]

    print(f"\n  Smoke test — abstract: '{test_abstract[:60]}...'")
    print(f"  {'Score':<8} Journal")
    print(f"  {'-'*60}")
    for idx in top_idx:
        print(f"  {scores[idx]:.4f}  {texts[idx][:80]}")


def main():
    print("\n=== STEP 2b: Precompute BERT Embeddings ===\n")

    # ── 1. Load data ──────────────────────────────────────────────────────
    print("[1/4] Loading dataset...")
    df = pd.read_csv(INPUT_FILE)
    print(f"  {len(df):,} journals loaded")

    # ── 2. Build bert_text ────────────────────────────────────────────────
    print("\n[2/4] Building bert_text field...")
    df["bert_text"] = df.apply(build_bert_text, axis=1)
    texts = df["bert_text"].tolist()
    print(f"  Sample: {texts[0]}")
    print(f"  Sample: {texts[100]}")

    # ── 3. Load model ─────────────────────────────────────────────────────
    print("\n[3/4] Loading BERT model...")
    model = load_model()

    # ── 4. Encode ─────────────────────────────────────────────────────────
    print("\n[4/4] Encoding journals...")
    embeddings = encode_journals(texts, model)

    # ── 5. Save ───────────────────────────────────────────────────────────
    print("\nSaving outputs...")
    save_outputs(embeddings, texts)

    # ── 6. Verify ─────────────────────────────────────────────────────────
    print("\nVerifying...")
    verify(embeddings, texts, model)

    print("\n✓ Step 2b complete.")
    print("  Files created:")
    print(f"    {EMBEDDINGS_FILE}  ← loaded at runtime for similarity search")
    print(f"    {TEXTS_FILE}       ← maps embedding row index to journal text")
    print("\n  Run step3b_bert_rerank.py next.\n")


if __name__ == "__main__":
    main()
