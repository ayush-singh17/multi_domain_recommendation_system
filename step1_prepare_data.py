"""
STEP 1 — Dataset Preparation
Journal Recommendation System

What this script does:
  - Filters journals only (removes book series, conference proceedings, etc.)
  - Fills missing Publisher and SJR values
  - Flags unranked journals (SJR Quartile = "-")
  - Creates journal_text field for BM25 indexing
  - Saves journals_clean.csv ready for Step 2
"""

import pandas as pd
import re

# ── Config ────────────────────────────────────────────────────────────────────
INPUT_FILE  = "journals.xlsx"
OUTPUT_FILE = "journals_clean.csv"
# ─────────────────────────────────────────────────────────────────────────────


def load_data(path):
    print(f"Loading: {path}")
    df = pd.read_excel(path)
    print(f"  Rows loaded: {len(df):,}")
    return df


def filter_journals(df):
    before = len(df)
    df = df[df["Type"].str.lower() == "journal"].copy()
    print(f"  Kept {len(df):,} journals  (removed {before - len(df):,} non-journal rows)")
    return df


def fix_missing_values(df):
    # Publisher: use Publisher.1 as fallback, then 'Unknown Publisher'
    df["Publisher"] = df["Publisher"].fillna(df["Publisher.1"])
    df["Publisher"] = df["Publisher"].fillna("Unknown Publisher")

    # SJR: fill missing with 0.0
    df["SJR"] = pd.to_numeric(df["SJR"], errors="coerce").fillna(0.0)

    # SJR Best Quartile: replace '-' with 'Unranked'
    df["SJR Best Quartile"] = df["SJR Best Quartile"].replace("-", "Unranked")

    # Drop the duplicate publisher column
    df = df.drop(columns=["Publisher.1"])

    print(f"  Missing values fixed. Nulls remaining: {df.isnull().sum().sum()}")
    return df


def create_journal_text(df):
    """
    Combines Title + Categories + Areas into one searchable text field.
    Strips quartile tags like (Q1), (Q2) so BM25 matches on topic words only.
    """

    def clean_field(text):
        if pd.isna(text):
            return ""
        text = re.sub(r"\(Q\d\)", "", str(text))   # remove (Q1), (Q2), etc.
        text = re.sub(r"[;|]", " ", text)           # remove separators
        return text.strip()

    df["journal_text"] = (
        df["Title"].apply(clean_field) + " " +
        df["Categories"].apply(clean_field) + " " +
        df["Areas"].apply(clean_field)
    ).str.lower().str.strip()

    print(f"  journal_text created.")
    print(f"  Sample: {df['journal_text'].iloc[0]}")
    return df


def save_data(df, path):
    df.to_csv(path, index=False)
    print(f"  Saved: {path}  ({len(df):,} rows)")


def main():
    print("\n=== STEP 1: Dataset Preparation ===\n")

    df = load_data(INPUT_FILE)
    df = filter_journals(df)
    df = fix_missing_values(df)
    df = create_journal_text(df)
    save_data(df, OUTPUT_FILE)

    print("\n✓ Step 1 complete. Run step2_build_index.py next.\n")


if __name__ == "__main__":
    main()
