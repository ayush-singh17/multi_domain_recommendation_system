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

// Input is already sorted by final score. Cap the whole mixed list, not each page.
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
