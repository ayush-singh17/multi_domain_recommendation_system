"""
BUILD JOURNAL TRENDS
Journal Recommendation System

What this script does:
  - Loads 5 years of SCImago CSV files (2020-2024)
  - Merges on Sourceid (most reliable key)
  - Creates journal_trends.csv with year-by-year metrics per journal

Output columns:
  Sourceid, Title, Issn,
  citations_2020..2024  (Citations / Doc. 2years per year)
  sjr_2020..2024        (SJR per year)
  docs_2020..2024       (Total Docs per year)
  trend_direction       (Up / Down / Stable based on citations)
  trend_pct             (% change 2020 → 2024)

Place the 5 CSV files in the same folder as this script:
  scimagojr_2020.csv
  scimagojr_2021.csv
  scimagojr_2022.csv
  scimagojr_2023.csv
  scimagojr_2024.csv
"""

import pandas as pd
import numpy as np
import os


YEARS      = [2020, 2021, 2022, 2023, 2024]
OUTPUT     = "journal_trends.csv"


def load_year(year: int) -> pd.DataFrame:
    path = f"scimagojr_{year}.csv"
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing: {path}")

    df = pd.read_csv(path, sep=';', low_memory=False)
    df = df[df['Type'].str.lower() == 'journal'].copy()

    # Fix European decimal formatting (comma → dot)
    for col in ['SJR', 'Citations / Doc. (2years)']:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(',', '.', regex=False),
            errors='coerce'
        )

    docs_col = f'Total Docs. ({year})'
    df[docs_col] = pd.to_numeric(df[docs_col], errors='coerce')

    return df[['Sourceid', 'Title', 'Issn', 'SJR',
               'Citations / Doc. (2years)', docs_col]].rename(columns={
        'SJR':                        f'sjr_{year}',
        'Citations / Doc. (2years)':  f'citations_{year}',
        docs_col:                     f'docs_{year}',
    })


def trend_direction(row) -> str:
    vals = [row[f'citations_{y}'] for y in YEARS]
    vals = [v for v in vals if pd.notna(v)]
    if len(vals) < 2:
        return 'Unknown'
    change = vals[-1] - vals[0]
    pct    = (change / vals[0] * 100) if vals[0] > 0 else 0
    if pct > 10:
        return 'Up'
    elif pct < -10:
        return 'Down'
    else:
        return 'Stable'


def trend_pct(row) -> float:
    start = row.get(f'citations_{YEARS[0]}')
    end   = row.get(f'citations_{YEARS[-1]}')
    if pd.isna(start) or pd.isna(end) or start == 0:
        return None
    return round((end - start) / start * 100, 1)


def main():
    print("\n=== BUILD JOURNAL TRENDS ===\n")

    # Load all years
    dfs = {}
    for year in YEARS:
        print(f"Loading {year}...")
        dfs[year] = load_year(year)
        print(f"  {len(dfs[year]):,} journals")

    # Merge on Sourceid — keep journals present in ALL 5 years
    print("\nMerging...")
    merged = dfs[2020]
    for year in YEARS[1:]:
        merged = merged.merge(
            dfs[year].drop(columns=['Title', 'Issn']),
            on='Sourceid',
            how='inner'
        )

    print(f"  Journals in all 5 years: {len(merged):,}")

    # Add trend signals
    merged['trend_direction'] = merged.apply(trend_direction, axis=1)
    merged['trend_pct']       = merged.apply(trend_pct, axis=1)

    # Save
    merged.to_csv(OUTPUT, index=False)
    print(f"\nSaved: {OUTPUT}  ({len(merged):,} journals)")

    # Summary
    print(f"\nTrend breakdown:")
    print(merged['trend_direction'].value_counts().to_string())

    # Sample
    print("\nSample — top 5 trending up journals:")
    top = merged[merged['trend_direction'] == 'Up'].nlargest(5, 'trend_pct')
    for _, row in top.iterrows():
        print(f"  +{row['trend_pct']}%  {row['Title']}")
        for y in YEARS:
            print(f"    {y}: Citations/Doc={row[f'citations_{y}']:.2f}  SJR={row[f'sjr_{y}']:.3f}")

    print("\n✓ Done. Use journal_trends.csv in the app.\n")


if __name__ == "__main__":
    main()
