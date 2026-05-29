"""
MERGE DOAJ APC DATA
Journal Recommendation System

What this script does:
  - Loads journalcsv__doaj_*.csv (DOAJ bulk data dump)
  - Merges with journals_clean.csv on ISSN
  - Adds columns: apc_usd, apc_currency, apc_raw, in_doaj
  - Saves updated journals_clean.csv

Run once after placing the DOAJ CSV in the same folder.
Download from: https://doaj.org/docs/public-data-dump/
"""

import pandas as pd
import glob


# ── Currency conversion to USD ────────────────────────────────────────────────
RATES = {
    "USD": 1.00, "EUR": 1.08, "GBP": 1.26, "CHF": 1.13,
    "JPY": 0.0067, "AUD": 0.65, "CAD": 0.74, "INR": 0.012,
    "CNY": 0.14, "BRL": 0.20, "KRW": 0.00075, "SEK": 0.096,
    "NOK": 0.095, "DKK": 0.145, "PLN": 0.25, "IDR": 0.000062,
    "IRR": 0.000024, "UAH": 0.024, "YER": 0.004, "MXN": 0.052,
    "TRY": 0.030, "ZAR": 0.055,
}


def find_doaj_file() -> str:
    for pattern in ["journalcsv__doaj*.csv", "doaj*.csv", "DOAJ*.csv"]:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    raise FileNotFoundError(
        "DOAJ CSV not found. Download from https://doaj.org/docs/public-data-dump/"
    )


def clean_issn(s) -> str:
    return str(s).replace("-", "").replace(" ", "").strip() if pd.notna(s) else ""


def parse_apc(apc_str) -> tuple:
    if pd.isna(apc_str) or str(apc_str).strip() == "":
        return None, None
    first = str(apc_str).split(";")[0].strip()
    parts = first.split()
    if len(parts) >= 2:
        try:
            amount   = float(parts[0].replace(",", ""))
            currency = parts[1].upper()
            usd      = int(round(amount * RATES.get(currency, 1.0)))
            return usd, currency
        except:
            pass
    return None, None


def main():
    print("\n=== MERGE DOAJ APC DATA ===\n")

    doaj_path = find_doaj_file()
    print(f"[1/4] DOAJ file: {doaj_path}")

    print("[2/4] Loading journals_clean.csv...")
    journals = pd.read_csv("journals_clean.csv")
    print(f"  {len(journals):,} journals")

    print("[3/4] Building DOAJ lookup...")
    doaj   = pd.read_csv(doaj_path, low_memory=False)
    lookup = {}
    for _, row in doaj.iterrows():
        issns    = [
            clean_issn(row.get("Journal ISSN (print version)", "")),
            clean_issn(row.get("Journal EISSN (online version)", "")),
        ]
        has_apc  = str(row.get("APC", "")).strip() == "Yes"
        apc_raw  = row.get("APC amount") if has_apc else None
        usd, cur = parse_apc(apc_raw) if has_apc else (0, "N/A")

        weeks = row.get("Average number of weeks between article submission and publication")
        try:
            weeks = int(weeks) if pd.notna(weeks) else None
        except:
            weeks = None

        for issn in issns:
            if issn and len(issn) == 8:
                lookup[issn] = {
                    "apc_usd":          usd,
                    "apc_currency":     cur,
                    "apc_raw":          apc_raw,
                    "weeks_to_publish": weeks,
                }
    print(f"  {len(lookup):,} ISSN entries built")

    print("[4/4] Merging...")
    rows = {"apc_usd": [], "apc_currency": [], "apc_raw": [], "weeks_to_publish": [], "in_doaj": []}

    for _, row in journals.iterrows():
        issns = [clean_issn(x) for x in str(row.get("Issn", "")).split(",")]
        found = next((lookup[i] for i in issns if i in lookup), None)
        if found:
            rows["apc_usd"].append(found["apc_usd"])
            rows["apc_currency"].append(found["apc_currency"])
            rows["apc_raw"].append(found["apc_raw"])
            rows["weeks_to_publish"].append(found.get("weeks_to_publish"))
            rows["in_doaj"].append(True)
        else:
            rows["apc_usd"].append(None)
            rows["apc_currency"].append(None)
            rows["apc_raw"].append(None)
            rows["weeks_to_publish"].append(None)
            rows["in_doaj"].append(False)

    for col, vals in rows.items():
        journals[col] = vals

    # Convert weeks to months for display (round to 1 decimal)
    journals["months_to_publish"] = journals["weeks_to_publish"].apply(
        lambda w: round(w / 4.33, 1) if w is not None and str(w) != "nan" else None
    )

    journals.to_csv("journals_clean.csv", index=False)

    # Summary
    matched = journals["in_doaj"].sum()
    has_apc = journals[(journals["apc_usd"].notna()) & (journals["apc_usd"] > 0)]
    free_oa = journals[journals["apc_usd"] == 0]

    print(f"\n  Matched to DOAJ : {matched:,} / {len(journals):,}")
    print(f"  With APC cost   : {len(has_apc):,}")
    print(f"  Free OA         : {len(free_oa):,}")
    if len(has_apc):
        print(f"  Avg APC (USD)   : ${has_apc['apc_usd'].mean():,.0f}")
        print(f"  Min / Max       : ${has_apc['apc_usd'].min():,} / ${has_apc['apc_usd'].max():,}")

    print("\n✓ journals_clean.csv updated with APC data.")
    print("  New columns: apc_usd, apc_currency, apc_raw, in_doaj\n")


if __name__ == "__main__":
    main()
