import { useEffect, useMemo, useState } from 'react';
import API from '../api/axios';
import { buildSequence, journalKey } from '../utils/results';

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function dateAfter(start, weeks) {
  if (!start) return 'Choose a start date';
  const date = new Date(`${start}T12:00:00`);
  date.setDate(date.getDate() + Math.round(weeks * 7));
  return Number.isNaN(date.getTime()) ? 'Choose a valid date'
    : date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}
const qClass = q => 'rv2-gantt-bar--' + String(q || 'unranked').toLowerCase();

function Gantt({ sequence, revisionWeeks }) {
  const total = Math.max(1, sequence[sequence.length - 1].endWeek);
  const step = [4, 8, 13, 26, 52, 104, 208].find(s => total / s <= 8) || 208;
  const ticks = [];
  for (let w = 0; w <= total; w += step) ticks.push(w);
  const pct = w => `${(w / total) * 100}%`;
  return (
    <div className="rv2-gantt" aria-label="Submission timeline chart">
      <div className="rv2-gantt-row rv2-gantt-row--axis">
        <span />
        <div className="rv2-gantt-axis">
          {ticks.map(w => <span key={w} style={{ left: pct(w) }}>wk {w}</span>)}
        </div>
      </div>
      {sequence.map((j, i) => (
        <div className="rv2-gantt-row" key={journalKey(j)}>
          <span className="rv2-gantt-label" title={j.title}>{j.position}. {j.title}</span>
          <div className="rv2-gantt-track">
            {ticks.map(w => <i key={w} className="rv2-gantt-grid" style={{ left: pct(w) }} />)}
            <div className={'rv2-gantt-bar ' + qClass(j.quartile)} style={{ left: pct(j.startWeek), width: pct(j.endWeek - j.startWeek) }}>
              {j.decisionWeeks}w
            </div>
            {i < sequence.length - 1 && Number(revisionWeeks) > 0 && (
              <div className="rv2-gantt-gap" title="Revision / reformatting" style={{ left: pct(j.endWeek), width: pct(Number(revisionWeeks)) }} />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function TimelineBuilder({ active, journals, onChange, onAdd, onGoToResults }) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [matches, setMatches] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [startDate, setStartDate] = useState(today);
  const [revisionWeeks, setRevisionWeeks] = useState(2);
  const sequence = useMemo(() => buildSequence(journals, revisionWeeks), [journals, revisionWeeks]);

  useEffect(() => {
    setSuggestions([]); setMatches(0); setError('');
    if (!active || query.trim().length < 2) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true);
    const timer = setTimeout(() => {
      API.get('/search/journals/', { params: { q: query.trim() }, signal: controller.signal })
        .then(({ data }) => { if (!controller.signal.aborted) { setSuggestions(data.journals || []); setMatches(data.total || 0); } })
        .catch(() => { if (!controller.signal.aborted) setError('Journal search is unavailable. Try again, or add journals from the Results tab.'); })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 300);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, active]);

  const move = (index, direction) => {
    const next = [...journals];
    [next[index], next[index + direction]] = [next[index + direction], next[index]];
    onChange(next);
  };
  const updateWeeks = (index, value) => {
    const number = Number(value);
    if (value !== '' && Number.isFinite(number) && number >= 1 && number <= 520) {
      onChange(journals.map((journal, i) => i === index ? { ...journal, decisionWeeks: number } : journal));
    }
  };
  const first = sequence[0];
  const last = sequence[sequence.length - 1];

  return (
    <div className="rv2-tl">
      <div className="rv2-tl-controls">
        <div className="rv2-tl-search">
          <label htmlFor="rv2-tl-search">Add a journal by name or ISSN</label>
          <input id="rv2-tl-search" className="rv2-input" type="search" value={query} autoComplete="off"
            onChange={e => setQuery(e.target.value)} placeholder="Type at least 2 characters, e.g. Computers in Biology…" />
          <p className="rv2-hint" role="status">
            {loading ? 'Searching journals…' : error || (query.trim().length >= 2
              ? `${matches} matches${matches > suggestions.length ? ` · showing ${suggestions.length}; narrow your search to find another` : ''}`
              : 'Or press “+ Timeline” on any journal in the Results tab.')}
          </p>
          {suggestions.length > 0 && (
            <ul className="rv2-suggest">
              {suggestions.map(journal => {
                const added = journals.some(j => journalKey(j) === journalKey(journal));
                return (
                  <li key={journalKey(journal)}>
                    <div><strong>{journal.title}</strong><small>{journal.quartile || 'Unranked'} · {journal.issn || 'No ISSN listed'}</small></div>
                    <button type="button" className="rv2-btn rv2-btn--ghost" disabled={added} onClick={() => onAdd(journal)}>{added ? 'Added' : 'Add'}</button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        <label className="rv2-field">First submission date
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
        </label>
        <label className="rv2-field">Revision gap between submissions (weeks)
          <input type="number" min="0" max="104" step="1" value={revisionWeeks} onChange={e => {
            const value = Number(e.target.value);
            if (Number.isFinite(value) && value >= 0 && value <= 104) setRevisionWeeks(value);
          }} />
        </label>
      </div>

      {journals.length === 0 ? (
        <div className="rv2-empty">
          <p><strong>Your timeline is empty.</strong></p>
          <p>Search for a journal above, or go to Results and press “+ Timeline” on the journals you want to plan around.</p>
          <button type="button" className="rv2-btn rv2-btn--primary" onClick={onGoToResults}>Browse results</button>
        </div>
      ) : (
        <>
          <div className="rv2-tl-summary">
            <div><span>Journals in sequence</span><strong>{journals.length}</strong></div>
            <div><span>Fastest: accepted at #1</span><strong>Week {first.endWeek}</strong><small>{dateAfter(startDate, first.endWeek)}</small></div>
            <div><span>Slowest: all earlier declined</span><strong>Week {last.endWeek}</strong><small>{dateAfter(startDate, last.endWeek)}</small></div>
          </div>

          <div className="rv2-tl-panel">
            <div className="rv2-tl-panel-head">
              <h3>Timeline</h3>
              <button type="button" className="rv2-link-btn" onClick={() => onChange([])}>Clear all</button>
            </div>
            <Gantt sequence={sequence} revisionWeeks={revisionWeeks} />
            <div className="rv2-gantt-legend">
              <span><i className="rv2-gantt-bar--q1" /> Q1</span><span><i className="rv2-gantt-bar--q2" /> Q2</span>
              <span><i className="rv2-gantt-bar--q3" /> Q3</span><span><i className="rv2-gantt-bar--q4" /> Q4</span>
              <span><i className="rv2-gantt-gap" /> Revision gap</span>
            </div>
          </div>

          <ol className="rv2-tl-list">
            {sequence.map((journal, index) => (
              <li key={journalKey(journal)} className="rv2-tl-item">
                <span className="rv2-step">{index + 1}</span>
                <div className="rv2-tl-info">
                  <strong>{journal.title}</strong>
                  <small>{journal.quartile || 'Unranked'} · {journal.issn}</small>
                </div>
                <label className="rv2-weeks">Decision time (weeks)
                  <input aria-label={`Decision weeks for ${journal.title}`} type="number" min="1" max="520" step="1"
                    value={journal.decisionWeeks} onChange={e => updateWeeks(index, e.target.value)} />
                </label>
                <div className="rv2-tl-dates">
                  <span>Submit <b>{dateAfter(startDate, journal.startWeek)}</b></span>
                  <span>Decision <b>{dateAfter(startDate, journal.endWeek)}</b></span>
                </div>
                <div className="rv2-tl-buttons">
                  <button type="button" disabled={index === 0} aria-label={`Move ${journal.title} earlier`} onClick={() => move(index, -1)}>↑</button>
                  <button type="button" disabled={index === journals.length - 1} aria-label={`Move ${journal.title} later`} onClick={() => move(index, 1)}>↓</button>
                  <button type="button" aria-label={`Remove ${journal.title}`} onClick={() => onChange(journals.filter((_, i) => i !== index))}>Remove</button>
                </div>
                {Number(journal.weeks_to_publish) > 0 && (
                  <small className="rv2-tl-ref">Dataset submission-to-publication reference: {journal.weeks_to_publish} weeks (not used as a decision time).</small>
                )}
              </li>
            ))}
          </ol>
        </>
      )}

      <p className="rv2-tl-note">
        Planning scenario only: the next submission starts after the previous journal declines and your revision gap ends.
        Decision times are editable assumptions based on quartile, not publisher promises or acceptance predictions.
        Publication after acceptance is additional and not included.
      </p>
    </div>
  );
}
