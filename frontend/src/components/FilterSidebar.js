const QUARTILES = ['Q1', 'Q2', 'Q3', 'Q4'];
const RISKS = ['Low', 'Medium'];

export default function FilterSidebar({
  facets, counts, onChange, onClear, limitLowTiers, onLimitChange, open, onClose, lowTierHidden,
}) {
  const toggleIn = (key, value) => onChange({
    ...facets,
    [key]: facets[key].includes(value) ? facets[key].filter(v => v !== value) : [...facets[key], value],
  });

  return (
    <aside className={'rv2-sidebar' + (open ? ' is-open' : '')} aria-label="Filter results">
      <div className="rv2-side-head">
        <h2>Filters</h2>
        <button type="button" className="rv2-link-btn" onClick={onClear}>Clear all</button>
        <button type="button" className="rv2-side-close" onClick={onClose} aria-label="Close filters">✕</button>
      </div>

      <input className="rv2-input" type="search" value={facets.query} placeholder="Search within results…"
        aria-label="Search within results" onChange={e => onChange({ ...facets, query: e.target.value })} />

      <fieldset className="rv2-fieldset">
        <legend>Quartile</legend>
        {QUARTILES.map(q => (
          <label key={q} className="rv2-check">
            <input type="checkbox" checked={facets.quartiles.includes(q)} onChange={() => toggleIn('quartiles', q)} />
            <span className={'rv2-dot rv2-dot--' + q.toLowerCase()} aria-hidden="true" />
            <span className="rv2-check-label">{q}</span>
            <em>{counts[q]}</em>
          </label>
        ))}
      </fieldset>

      <fieldset className="rv2-fieldset">
        <legend>Risk level</legend>
        {RISKS.map(r => (
          <label key={r} className="rv2-check">
            <input type="checkbox" checked={facets.risks.includes(r)} onChange={() => toggleIn('risks', r)} />
            <span className={'rv2-dot rv2-dot--' + (r === 'Low' ? 'low' : 'med')} aria-hidden="true" />
            <span className="rv2-check-label">{r} risk</span>
            <em>{counts[r]}</em>
          </label>
        ))}
      </fieldset>

      <fieldset className="rv2-fieldset">
        <legend>More</legend>
        <label className="rv2-check">
          <input type="checkbox" checked={facets.mahe} onChange={() => onChange({ ...facets, mahe: !facets.mahe })} />
          <span className="rv2-check-label">MAHE approved</span><em>{counts.mahe}</em>
        </label>
        <label className="rv2-check">
          <input type="checkbox" checked={facets.oa} onChange={() => onChange({ ...facets, oa: !facets.oa })} />
          <span className="rv2-check-label">Open access</span><em>{counts.oa}</em>
        </label>
      </fieldset>

      <div className="rv2-fieldset rv2-fieldset--note">
        <label className="rv2-check rv2-check--top">
          <input type="checkbox" checked={limitLowTiers} onChange={e => onLimitChange(e.target.checked)} />
          <span className="rv2-check-label">Limit Q3 and Q4 to 2 each</span>
        </label>
        <p className="rv2-hint">
          {limitLowTiers
            ? `Keeps the list focused on stronger journals${lowTierHidden > 0 ? ` (${lowTierHidden} lower-quartile matches hidden)` : ''}. Untick to see every match.`
            : 'Showing every match in every quartile.'}
        </p>
      </div>
    </aside>
  );
}
