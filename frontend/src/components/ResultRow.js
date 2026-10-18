import JournalCard from './JournalCard';

const num = (v, d = 2) => (v == null || v === '' || Number.isNaN(Number(v))) ? '—' : Number(v).toFixed(d);
const shortAreas = areas => String(areas || '').split(',').map(a => a.trim()).filter(Boolean).slice(0, 2).join(' · ');

export default function ResultRow({
  journal, position, expanded, onToggle, inTimeline, onAddTimeline, compared, onCompare,
}) {
  const quartile = journal.quartile || 'Unranked';
  const risk = journal.risk_level;
  const predatory = journal.predatory_level && journal.predatory_level !== 'Clear' ? journal.predatory_level : null;
  const score = Math.round((journal.final_score ?? 0) * 100);
  const detailsId = `rv2-details-${position}`;

  return (
    <article className={'rv2-row rv2-row--' + quartile.toLowerCase() + (expanded ? ' is-expanded' : '')}>
      <div className="rv2-row-main">
        <div className="rv2-rank" aria-label={`Result ${position}`}>{position}</div>

        <div className="rv2-row-body">
          <h3 className="rv2-title">
            {journal.title}
            {journal.homepage_url && (
              <a className="rv2-visit" href={journal.homepage_url} target="_blank" rel="noopener noreferrer"
                 aria-label={`Visit ${journal.title} website`} title="Visit journal website">↗</a>
            )}
          </h3>
          <p className="rv2-sub">
            {[journal.publisher, shortAreas(journal.areas)].filter(Boolean).join('  ·  ')}
          </p>
          <div className="rv2-badges">
            <span className={'rv2-badge rv2-badge--' + quartile.toLowerCase()}>{quartile}</span>
            {risk && <span className={'rv2-badge rv2-badge--risk-' + risk.toLowerCase()}>{risk} risk</span>}
            {Number(journal.mahe_approved) === 1 && <span className="rv2-badge rv2-badge--mahe">MAHE ✓</span>}
            {journal.open_access === 'Yes' && <span className="rv2-badge rv2-badge--oa">Open access</span>}
            {predatory && <span className="rv2-badge rv2-badge--warn">⚠ {predatory}</span>}
          </div>
        </div>

        <dl className="rv2-metrics">
          <div className="rv2-metric rv2-metric--score"><dt>Match</dt><dd>{score}%</dd></div>
          <div className="rv2-metric"><dt>SJR</dt><dd>{num(journal.sjr)}</dd></div>
          <div className="rv2-metric"><dt>H-index</dt><dd>{journal.h_index != null ? Math.round(journal.h_index) : '—'}</dd></div>
        </dl>

        <div className="rv2-actions">
          <button type="button" className={'rv2-btn rv2-btn--primary' + (inTimeline ? ' is-done' : '')}
            disabled={inTimeline} onClick={onAddTimeline}>
            {inTimeline ? '✓ In timeline' : '+ Timeline'}
          </button>
          <label className="rv2-compare">
            <input type="checkbox" checked={compared} onChange={onCompare} /> Compare
          </label>
          <button type="button" className="rv2-btn rv2-btn--ghost" aria-expanded={expanded} aria-controls={detailsId}
            onClick={onToggle}>
            {expanded ? 'Hide details ▴' : 'Details ▾'}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="rv2-details" id={detailsId}>
          <JournalCard journal={journal} planKey={journal._plan} onCompareToggle={onCompare} isCompared={compared} />
        </div>
      )}
    </article>
  );
}
