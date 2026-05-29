"""
IMPORT MANUAL METRICS
Journal Recommendation System

Run this AFTER you have filled in citescore and impact_factor
in top_300_journals.csv.

What this script does:
  - Reads your filled top_300_journals.csv
  - Merges citescore and impact_factor into journals_clean.csv using ISSN
  - Saves updated journals_clean.csv
"""

import pandas as pd


def clean_issn(s) -> str:
    return str(s).replace("-", "").replace(" ", "").strip() if pd.notna(s) else ""


def main():
    print("\n=== IMPORT MANUAL METRICS ===\n")

    df      = pd.read_csv("journals_clean.csv")
    manual  = pd.read_csv("top_300_journals.csv")

    # Only rows where something was filled in
    filled = manual[
        manual["citescore"].notna() | manual["impact_factor"].notna()
    ]
    print(f"Filled entries found: {len(filled)}")

    if len(filled) == 0:
        print("Nothing to import — fill in top_300_journals.csv first.")
        return

    # Build lookup by ISSN
    lookup = {}
    for _, row in filled.iterrows():
        issns = [clean_issn(x) for x in str(row["Issn"]).split(",")]
        for issn in issns:
            if issn:
                lookup[issn] = {
                    "citescore":     row.get("citescore"),
                    "impact_factor": row.get("impact_factor"),
                }

    # Merge into main dataset
    updated = 0
    for i, row in df.iterrows():
        issns = [clean_issn(x) for x in str(row["Issn"]).split(",")]
        for issn in issns:
            if issn in lookup:
                df.at[i, "citescore"]     = lookup[issn]["citescore"]
                df.at[i, "impact_factor"] = lookup[issn]["impact_factor"]
                updated += 1
                break

    df.to_csv("journals_clean.csv", index=False)

    has_cs = df["citescore"].notna().sum()
    has_if = df["impact_factor"].notna().sum()
    print(f"Updated rows      : {updated}")
    print(f"With CiteScore    : {has_cs}")
    print(f"With Impact Factor: {has_if}")
    print("\n✓ journals_clean.csv updated with manual metrics.\n")


if __name__ == "__main__":
    main()
