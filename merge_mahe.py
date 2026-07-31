"""
merge_mahe.py — Add MAHE Approved column to journals_clean.csv

Reads the MAHE Approved list (Excel), builds a set of all ISSNs,
then cross-references against journals_clean.csv to flag matching journals.

Run once:
    python merge_mahe.py
"""

import pandas as pd
import os

MAHE_FILE  = "MAHEApprovedlist_Jan_2026.xlsx"
CSV_FILE   = "journals_clean.csv"


def normalise_issn(val):
    """Strip dashes, spaces, and lowercase an ISSN string."""
    if pd.isna(val):
        return ""
    return str(val).replace("-", "").replace(" ", "").strip().upper()


def main():
    # ── 1. Build the MAHE ISSN set ────────────────────────────────────────────
    print(f"Reading {MAHE_FILE}...")
    mahe = pd.read_excel(MAHE_FILE)
    print(f"  MAHE list rows: {len(mahe):,}")

    mahe_issns = set()
    for col in ["Print ISSN", "E-ISSN"]:
        if col in mahe.columns:
            for val in mahe[col].dropna():
                norm = normalise_issn(val)
                if norm and len(norm) >= 7:  # valid ISSN is 8 chars
                    mahe_issns.add(norm)

    print(f"  Unique MAHE ISSNs: {len(mahe_issns):,}")

    # ── 2. Read journals_clean.csv and match ──────────────────────────────────
    print(f"\nReading {CSV_FILE}...")
    df = pd.read_csv(CSV_FILE)
    print(f"  Journals: {len(df):,}")

    def is_mahe_approved(issn_field):
        """Check if any ISSN in the comma-separated field is in the MAHE set."""
        if pd.isna(issn_field):
            return 0
        parts = str(issn_field).replace("-", "").split(",")
        for part in parts:
            norm = part.strip().upper()
            if norm in mahe_issns:
                return 1
        return 0

    df["mahe_approved"] = df["Issn"].apply(is_mahe_approved)

    matched = df["mahe_approved"].sum()
    print(f"\n  ✓ MAHE Approved matches: {matched:,} / {len(df):,} journals")
    print(f"  ✓ Match rate: {matched / len(df) * 100:.1f}%")

    # ── 3. Save back ─────────────────────────────────────────────────────────
    df.to_csv(CSV_FILE, index=False)
    print(f"\n  ✓ Saved updated {CSV_FILE} with 'mahe_approved' column")


if __name__ == "__main__":
    main()
