"""
ADD CITESCORE AND IMPACT FACTOR
Journal Recommendation System

Your professor's recommendation: manually enter CiteScore and Impact Factor
for the top 300 journals rather than trying to scrape all 29,553.

What this script does:
  - Adds two empty columns to journals_clean.csv:
      citescore      → Elsevier CiteScore (from Scopus)
      impact_factor  → Clarivate Impact Factor (from Web of Science)
  - Exports top_300_journals.csv — the 300 highest-ranked journals
    by SJR for you to fill in manually
  - After you fill in the CSV, run: python import_manual_metrics.py

Sources to look up values:
  CiteScore  → https://www.scopus.com/sources
  Impact Factor → https://jcr.clarivate.com (needs institutional access)
                  OR Google "<journal name> impact factor <year>"
"""

import pandas as pd


def main():
    print("\n=== ADD CITESCORE / IMPACT FACTOR COLUMNS ===\n")

    df = pd.read_csv("journals_clean.csv")
    print(f"Loaded {len(df):,} journals")

    # Add empty columns if not already present
    if "citescore" not in df.columns:
        df["citescore"] = None
        print("  Added: citescore column")

    if "impact_factor" not in df.columns:
        df["impact_factor"] = None
        print("  Added: impact_factor column")

    df.to_csv("journals_clean.csv", index=False)
    print("  journals_clean.csv updated")

    # Export top 300 by SJR for manual entry
    top300 = (
        df[df["SJR Best Quartile"] == "Q1"]
        .sort_values("SJR", ascending=False)
        .head(300)[["Title", "Publisher", "Issn", "SJR", "H index",
                     "Areas", "Coverage", "citescore", "impact_factor"]]
        .copy()
    )

    top300.to_csv("top_300_journals.csv", index=False)
    print(f"\n  Exported: top_300_journals.csv ({len(top300)} journals)")
    print("\nNext steps:")
    print("  1. Open top_300_journals.csv in Excel")
    print("  2. Fill in citescore and impact_factor columns")
    print("  3. Run: python import_manual_metrics.py")


if __name__ == "__main__":
    main()
