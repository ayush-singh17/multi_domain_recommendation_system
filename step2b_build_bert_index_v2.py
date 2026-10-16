"""
STEP 2b (v2) — Embed the ENRICHED journal text with SPECTER2

Reads  : journals_clean_v2.csv   (made by: python collect_all.py --build)
Embeds : journal_text_v2         (title + categories + areas + OpenAlex topics/keywords/titles)
Writes : journal_embeddings_v2.npy  (N x 768)   and   bert_texts_v2.pkl

Your existing journal_embeddings.npy / bert_texts.pkl are NOT touched, so you can
compare or roll back. Row order is identical to journals_clean.csv.

Texts are ~10x longer than before (up to 512 tokens), so this is much slower than the
original step2b. Use a GPU if you can (e.g. a free Colab/Kaggle GPU). The script saves
progress in chunks (emb_v2_parts/) and resumes if interrupted.

    pip install sentence-transformers numpy pandas
    python step2b_build_bert_index_v2.py
"""

import os
import pickle
import time

import numpy as np
import pandas as pd

INPUT_FILE = "journals_clean_v2.csv"
EMB_OUT = "journal_embeddings_v2.npy"
TEXT_OUT = "bert_texts_v2.pkl"
PARTS_DIR = "emb_v2_parts"
MODEL_NAME = "allenai/specter2_base"     # same model/call as the app uses
CHUNK = 2048
BATCH_SIZE = 32                          # long texts: keep batches small (raise on a big GPU)


def load_model():
    from sentence_transformers import SentenceTransformer
    import torch
    model = SentenceTransformer(MODEL_NAME)
    model.max_seq_length = 512
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  Device: {dev}" + ("" if dev == "cuda" else "  (CPU: expect many hours)"))
    return model.to(torch.device(dev))


def main(model=None):
    df = pd.read_csv(INPUT_FILE, low_memory=False)
    texts = df["journal_text_v2"].fillna("").astype(str).tolist()
    n = len(texts)
    print(f"{n:,} journals | enriched: {(df.oa_match_status.str.startswith('matched')).sum():,}")
    model = model or load_model()

    os.makedirs(PARTS_DIR, exist_ok=True)
    start = time.time()
    for ci, lo in enumerate(range(0, n, CHUNK)):
        part = os.path.join(PARTS_DIR, f"part_{ci:04d}.npy")
        if os.path.exists(part):
            continue                                            # resume
        emb = model.encode(texts[lo:lo + CHUNK], convert_to_numpy=True, batch_size=BATCH_SIZE,
                           normalize_embeddings=True, show_progress_bar=False)
        np.save(part, emb.astype(np.float32))
        done = min(lo + CHUNK, n)
        el = time.time() - start
        print(f"  {done:>6,}/{n:,}  elapsed {el/60:.1f} min")

    parts = sorted(os.listdir(PARTS_DIR))
    embs = np.vstack([np.load(os.path.join(PARTS_DIR, p)) for p in parts])
    assert embs.shape == (n, 768), f"shape {embs.shape} != ({n}, 768)"
    np.save(EMB_OUT, embs)
    pickle.dump(texts, open(TEXT_OUT, "wb"))
    print(f"\nSaved {EMB_OUT} {embs.shape} and {TEXT_OUT}")
    print("To switch the app over: back up the old journal_embeddings.npy and bert_texts.pkl, "
          "then rename the *_v2 files to the old names. Restart the ML service.")


if __name__ == "__main__":
    main()
