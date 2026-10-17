"""Local journal catalogue lookup; no scraping or model inference required."""

def search_catalog(df, query, limit=20):
    query = str(query).strip().casefold()
    if len(query) < 2:
        return {"journals": [], "total": 0}
    titles = df["Title"].fillna("").astype(str)
    issns = df["Issn"].fillna("").astype(str)
    title_match = titles.str.casefold().str.contains(query, regex=False)
    issn_match = issns.str.casefold().str.replace("-", "", regex=False).str.contains(query.replace("-", ""), regex=False) if query.replace("-", "") else title_match & False
    matches = df.loc[title_match | issn_match].copy()
    matches["_exact"] = matches["Title"].fillna("").astype(str).str.casefold().eq(query)
    matches = matches.sort_values(["_exact", "Title"], ascending=[False, True], kind="stable")
    return {
        "total": len(matches),
        "journals": [{
            "title": row["Title"],
            "issn": row.get("Issn", ""),
            "quartile": row.get("SJR Best Quartile", "Unranked"),
            "weeks_to_publish": row.get("weeks_to_publish", None),
        } for _, row in matches.head(limit).iterrows()],
    }
