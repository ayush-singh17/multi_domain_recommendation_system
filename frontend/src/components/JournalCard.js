import { useState, Fragment } from 'react';
import TrendChart from './TrendChart';

// ── Predatory warning (collapsible) ──────────────────────────────────────────
function PredatoryWarning({ level, flags, score }) {
  const [open, setOpen] = useState(false);
  if (!level || level === 'Clear') return null;
  const isPred = level === 'Potentially Predatory';
  const color  = isPred ? 'var(--rose)' : 'var(--amber)';
  const cls    = isPred ? 'level-predatory' : 'level-caution';
  return (
    <div className={'predatory-warning ' + cls} onClick={() => setOpen(!open)}>
      <div className="pw-header">
        <div className="pw-title" style={{color}}>
          {isPred ? '🚨' : '⚠️'} {level} — {score}/100
        </div>
        <span className="pw-toggle" style={{color}}>{open ? '▲' : '▼'}</span>
      </div>
      {open && flags?.length > 0 && (
        <div className="pw-flags">
          {flags.map((f,i) => <div key={i} className="pw-flag" style={{color}}>{f}</div>)}
          <div className="pw-note">Shown for transparency. Verify independently before submitting.</div>
        </div>
      )}
    </div>
  );
}

// ── Single metric cell ────────────────────────────────────────────────────────
function MetaCell({ label, value, accent }) {
  return (
    <div className="jc-meta-cell">
      <span className="jc-meta-label">{label}</span>
      <span className="jc-meta-value" style={accent ? {color: accent} : undefined}>
        {value ?? '—'}
      </span>
    </div>
  );
}

// ── Main card ─────────────────────────────────────────────────────────────────
export default function JournalCard({ journal, planKey, onCompareToggle, isCompared }) {
  const [whyOpen, setWhyOpen] = useState(false);

  const scorePct = Math.round((journal.final_score ?? 0) * 100);
  const riskColor = { Low: 'var(--emerald)', Medium: 'var(--amber)', High: 'var(--rose)' }[journal.risk_level] || 'var(--text-3)';
  const quartileColor = { Q1: 'var(--indigo)', Q2: 'var(--emerald)', Q3: 'var(--amber)', Q4: 'var(--rose)' }[journal.quartile] || 'var(--text-3)';
  const weeksVal = journal.weeks_to_publish ? parseFloat(journal.weeks_to_publish) : null;

  // APC display
  const apcDisplay = journal.open_access === 'Yes'
    ? (journal.apc_usd > 0 ? `$${journal.apc_usd.toLocaleString()}` : 'Free')
    : 'N/A (Subscription)';

  // ── Collect present primary metrics ──
  const metrics = [];
  const isValidValue = (val) => val != null && val !== '' && val !== '—' && val !== 'None';

  if (isValidValue(journal.impact_factor)) {
    metrics.push({
      label: 'Impact Factor',
      value: journal.impact_factor,
    });
  }
  if (isValidValue(journal.citescore)) {
    metrics.push({
      label: 'CiteScore',
      value: journal.citescore,
    });
  }
  if (isValidValue(journal.sjr)) {
    metrics.push({
      label: 'SJR',
      value: journal.sjr,
    });
  }
  if (isValidValue(journal.h_index)) {
    metrics.push({
      label: 'H-index',
      value: journal.h_index,
    });
  }
  if (weeksVal != null && isValidValue(journal.weeks_to_publish)) {
    metrics.push({
      label: 'Time to Review',
      value: `~${weeksVal}w`,
    });
  }
  if (isValidValue(journal.open_access)) {
    metrics.push({
      label: 'APC',
      value: apcDisplay,
      style: journal.open_access === 'Yes' && journal.apc_usd === 0 ? { color: 'var(--emerald)' } : undefined,
    });
  }

  return (
    <div className={'jc-card' + (isCompared ? ' jc-card-compared' : '')}>

      {/* ── Top bar: journal name + match % + quartile + risk ── */}
      <div className="jc-top">
        <div className="jc-title-block">
          <div className="jc-title">{journal.title}</div>
          <div className="jc-publisher">{journal.publisher || '—'}</div>
          {journal.homepage_url && (
            <a
              href={journal.homepage_url}
              target="_blank"
              rel="noopener noreferrer"
              className="jc-homepage-link"
              onClick={e => e.stopPropagation()}
            >
              <svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                <path d="M5 2H2a1 1 0 00-1 1v7a1 1 0 001 1h7a1 1 0 001-1V7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                <path d="M8 1h3v3M11 1L6 6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Visit Journal
            </a>
          )}
        </div>

        <div className="jc-badges">
          {/* Match score */}
          <div className="jc-match">
            <span className="jc-match-num">{scorePct}%</span>
            <span className="jc-match-label">Match</span>
          </div>

          {/* Quartile */}
          <div className="jc-badge" style={{color: quartileColor, borderColor: quartileColor + '40', background: quartileColor + '12'}}>
            {journal.quartile || '—'}
          </div>

          {/* Risk */}
          <div className="jc-badge" style={{color: riskColor, borderColor: riskColor + '40', background: riskColor + '12'}}>
            {journal.risk_level || '—'} Risk
          </div>
        </div>
      </div>

      {/* Predatory warning */}
      <PredatoryWarning level={journal.predatory_level} flags={journal.predatory_flags} score={journal.predatory_score} />

      {/* ── Primary metrics row ── */}
      {metrics.length > 0 && (
        <div className="jc-primary-metrics">
          {metrics.map((m, idx) => (
            <Fragment key={m.label}>
              <div className="jc-primary-cell">
                <span className="jc-primary-label">{m.label}</span>
                <span className="jc-primary-value" style={m.style}>
                  {m.value}
                </span>
              </div>
              {idx < metrics.length - 1 && <div className="jc-divider" />}
            </Fragment>
          ))}
        </div>
      )}

      {/* ── Secondary info grid ── */}
      <div className="jc-meta-grid">
        <MetaCell label="ISSN"        value={journal.issn} />
        <MetaCell label="Open Access" value={journal.open_access === 'Yes' ? '✓ Yes' : '✗ No'} accent={journal.open_access === 'Yes' ? 'var(--emerald)' : undefined} />
        <MetaCell label="Categories"  value={journal.areas} />
      </div>



      {/* ── Why Recommended accordion ── */}
      <div className="why-accordion">
        <div className="why-header" onClick={() => setWhyOpen(!whyOpen)}>
          Why Recommended
          <span className={'why-chevron' + (whyOpen ? ' open' : '')}>▼</span>
        </div>
        {whyOpen && (
          <div className="why-body">
            {journal.matched_tokens?.length > 0 && (
              <div className="why-tokens">
                {journal.matched_tokens.map(t => <span key={t} className="why-token">{t}</span>)}
              </div>
            )}
            <p className="why-relevance">{journal.relevance}</p>
            <div className="why-signals">
              {journal.risk_signals?.map((s,i) => (
                <div key={i} className={s.startsWith('✓') ? 'signal-ok' : s.startsWith('~') ? 'signal-warn' : 'signal-bad'}>{s}</div>
              ))}
            </div>
            <div className="score-breakdown">{journal.score_breakdown}</div>
          </div>
        )}
      </div>

      {/* ── TrendChart (full chart, collapsible via TrendChart itself) ── */}
      <TrendChart issn={journal.issn} title={journal.title} />

      {/* ── Actions ── */}
      <div className="card-actions">
        <button
          className={isCompared ? 'btn-compare-active' : 'btn-compare'}
          onClick={() => onCompareToggle && onCompareToggle(journal)}
        >
          ⇄ {isCompared ? 'Comparing' : 'Compare'}
        </button>
        {journal.homepage_url && (
          <a
            href={journal.homepage_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-visit-journal"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path d="M5 2H2a1 1 0 00-1 1v7a1 1 0 001 1h7a1 1 0 001-1V7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
              <path d="M8 1h3v3M11 1L6 6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Visit Journal
          </a>
        )}
      </div>
    </div>
  );
}
