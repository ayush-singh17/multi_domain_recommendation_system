export const journalKey = j => `${String(j.issn || '').trim()}|${String(j.title || '').trim().toLowerCase()}`;

export function rankedJournals(plans) {
  const unique = new Map();
  for (const plan of ['A', 'B', 'C']) {
    for (const journal of plans[plan] || []) {
      const key = journalKey(journal);
      if (!unique.has(key)) unique.set(key, { ...journal, _plan: plan });
    }
  }
  return [...unique.values()].sort((a, b) =>
    Number(b.final_score || 0) - Number(a.final_score || 0) || a.title.localeCompare(b.title));
}

// Numeric filters chosen on the Search page (kept from the previous version).
export function filterJournals(journals, minHIndex, minSJR, tag) {
  return journals.filter(j => {
    if (minHIndex > 0 && !(j.h_index != null && Number(j.h_index) >= minHIndex)) return false;
    if (minSJR > 0 && !(j.sjr != null && Number(j.sjr) >= minSJR)) return false;
    if (['Q1', 'Q2', 'Q3', 'Q4'].includes(tag)) return j.quartile === tag;
    if (tag === 'Low Risk') return j.risk_level === 'Low';
    if (tag === 'Medium Risk') return j.risk_level === 'Medium';
    if (tag === 'MAHE Approved') return Number(j.mahe_approved) === 1;
    return true;
  });
}

// Input is already sorted. Keeps at most 2 Q3 and 2 Q4 journals in the whole list.
export function capDefaultMix(journals) {
  const kept = { Q3: 0, Q4: 0 };
  return journals.filter(journal => {
    if (!Object.prototype.hasOwnProperty.call(kept, journal.quartile)) return true;
    return kept[journal.quartile]++ < 2;
  });
}

// These are planning assumptions, not measured review or acceptance times.
export function timelineEntry(journal) {
  const defaults = { Q1: 20, Q2: 16, Q3: 12, Q4: 10 };
  return { ...journal, decisionWeeks: defaults[journal.quartile] || 16 };
}

export function buildSequence(journals, revisionWeeks) {
  let elapsed = 0;
  return journals.map((journal, index) => {
    const startWeek = elapsed;
    const endWeek = startWeek + Number(journal.decisionWeeks);
    elapsed = endWeek + Number(revisionWeeks);
    return { ...journal, position: index + 1, startWeek, endWeek };
  });
}

/* ───────────── Sorting and multi-select facets (new) ───────────── */

export const SORT_OPTIONS = [
  ['best', 'Best match'],
  ['sjr', 'SJR: high to low'],
  ['h', 'H-index: high to low'],
  ['az', 'Title: A to Z'],
];

export function sortJournals(journals, key) {
  const num = v => Number(v ?? 0) || 0;
  const copy = [...journals];
  if (key === 'sjr') copy.sort((a, b) => num(b.sjr) - num(a.sjr) || a.title.localeCompare(b.title));
  else if (key === 'h') copy.sort((a, b) => num(b.h_index) - num(a.h_index) || a.title.localeCompare(b.title));
  else if (key === 'az') copy.sort((a, b) => a.title.localeCompare(b.title));
  return copy; // 'best' keeps the incoming (ranked) order
}

export const emptyFacets = () => ({ quartiles: [], risks: [], mahe: false, oa: false, query: '' });

export const hasActiveFacets = f =>
  f.quartiles.length > 0 || f.risks.length > 0 || f.mahe || f.oa || f.query.trim() !== '';

// `skip` lets us count a facet's options while ignoring that facet itself.
export function matchesFacets(j, f, skip) {
  if (skip !== 'quartiles' && f.quartiles.length && !f.quartiles.includes(j.quartile)) return false;
  if (skip !== 'risks' && f.risks.length && !f.risks.includes(j.risk_level)) return false;
  if (skip !== 'mahe' && f.mahe && Number(j.mahe_approved) !== 1) return false;
  if (skip !== 'oa' && f.oa && j.open_access !== 'Yes') return false;
  const q = f.query.trim().toLowerCase();
  if (skip !== 'query' && q) {
    const haystack = `${j.title} ${j.publisher || ''} ${j.areas || ''} ${j.issn || ''}`.toLowerCase();
    if (!haystack.includes(q)) return false;
  }
  return true;
}

export function facetCounts(journals, f) {
  const count = (skip, pred) => journals.filter(j => matchesFacets(j, f, skip) && pred(j)).length;
  return {
    Q1: count('quartiles', j => j.quartile === 'Q1'),
    Q2: count('quartiles', j => j.quartile === 'Q2'),
    Q3: count('quartiles', j => j.quartile === 'Q3'),
    Q4: count('quartiles', j => j.quartile === 'Q4'),
    Low: count('risks', j => j.risk_level === 'Low'),
    Medium: count('risks', j => j.risk_level === 'Medium'),
    mahe: count('mahe', j => Number(j.mahe_approved) === 1),
    oa: count('oa', j => j.open_access === 'Yes'),
  };
}

// limitLowTiers = keep at most 2 Q3 + 2 Q4, unless the user explicitly picked Q3 or Q4.
export function applyFacets(journals, f, limitLowTiers) {
  const matched = journals.filter(j => matchesFacets(j, f));
  const lowTierChosen = f.quartiles.includes('Q3') || f.quartiles.includes('Q4');
  return limitLowTiers && !lowTierChosen ? capDefaultMix(matched) : matched;
}
