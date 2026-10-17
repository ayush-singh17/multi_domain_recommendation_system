import { useEffect, useMemo, useState } from 'react';
import API from '../api/axios';
import { buildSequence, journalKey } from '../utils/results';

function today() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
function dateAfter(start, weeks) {
  if (!start) return 'Choose a start date';
  const date = new Date(`${start}T12:00:00`);
  date.setDate(date.getDate() + Math.round(weeks * 7));
  return Number.isNaN(date.getTime()) ? 'Choose a valid date' : date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

export default function TimelineBuilder({ active, journals, onChange, onAdd }) {
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
  return <div className="timeline-builder">
    <h2>Build your submission timeline</h2>
    <p>Select journals from the dataset, then arrange the order you would try them. Add as many as you need.</p>
    <label className="timeline-search-label" htmlFor="timeline-search">Journal name or ISSN</label>
    <input id="timeline-search" type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Type at least 2 characters, e.g. Computers in Biology…" autoComplete="off" />
    <div role="status" className="timeline-search-status">
      {loading ? 'Searching journals…' : error || (query.trim().length >= 2 ? `${matches} matches${matches > suggestions.length ? ` · showing ${suggestions.length}; narrow your search to find another journal` : ''}` : 'Search includes journals beyond your current recommendations.')}
    </div>
    {suggestions.length > 0 && <ul className="timeline-suggestions">
      {suggestions.map(journal => {
        const added = journals.some(j => journalKey(j) === journalKey(journal));
        return <li key={journalKey(journal)}><div><strong>{journal.title}</strong><small>{journal.quartile || 'Unranked'} · {journal.issn || 'No ISSN listed'}</small></div><button type="button" className="btn-secondary" disabled={added} onClick={() => onAdd(journal)}>{added ? 'Added' : 'Add'}</button></li>;
      })}
    </ul>}

    <div className="timeline-settings">
      <label>First submission date <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} /></label>
      <label>Revision / reformatting between submissions (weeks) <input type="number" min="0" max="104" step="1" value={revisionWeeks} onChange={e => {
        const value = Number(e.target.value);
        if (Number.isFinite(value) && value >= 0 && value <= 104) setRevisionWeeks(value);
      }} /></label>
    </div>
    <p className="timeline-assumptions">This is a sequential planning scenario: the next submission starts after the previous journal declines and your revision period ends. Decision times are editable assumptions based on quartile, not publisher promises or acceptance predictions. Publication-time data, where available, is shown separately because it is not a time-to-decision measurement.</p>
    {journals.length === 0 ? <div className="timeline-empty">Add journals above or use “Add to timeline” in Results to begin.</div> : <>
      <div className="timeline-sequence-header"><h3>Your sequence ({journals.length})</h3><button type="button" className="btn-secondary" onClick={() => onChange([])}>Clear sequence</button></div>
      <ol className="timeline-sequence">
        {sequence.map((journal, index) => <li key={journalKey(journal)}>
          <div className="timeline-journal-heading"><span className="timeline-step">{index + 1}</span><div><strong>{journal.title}</strong><small>{journal.quartile || 'Unranked'} · {journal.issn}</small></div></div>
          <div className="timeline-row-controls">
            <label>Assumed decision time (weeks) <input aria-label={`Decision weeks for ${journal.title}`} type="number" min="1" max="520" step="1" value={journal.decisionWeeks} onChange={e => updateWeeks(index, e.target.value)} /></label>
            <div className="timeline-order-buttons">
              <button type="button" disabled={index === 0} aria-label={`Move ${journal.title} earlier`} onClick={() => move(index, -1)}>↑ Earlier</button>
              <button type="button" disabled={index === journals.length - 1} aria-label={`Move ${journal.title} later`} onClick={() => move(index, 1)}>↓ Later</button>
              <button type="button" aria-label={`Remove ${journal.title}`} onClick={() => onChange(journals.filter((_, i) => i !== index))}>Remove</button>
            </div>
          </div>
          <div className="timeline-window"><span>Submit: <strong>{dateAfter(startDate, journal.startWeek)}</strong> (week {journal.startWeek})</span><span>Estimated decision: <strong>{dateAfter(startDate, journal.endWeek)}</strong> (week {journal.endWeek})</span></div>
          {Number(journal.weeks_to_publish) > 0 && <small className="timeline-reference">Dataset submission-to-publication reference: {journal.weeks_to_publish} weeks. This value is not used as a rejection / review duration.</small>}
        </li>)}
      </ol>
      <div className="timeline-total" aria-live="polite">If every earlier submission is declined, the estimated decision from the last journal is at <strong>week {sequence[sequence.length - 1].endWeek}</strong> — {dateAfter(startDate, sequence[sequence.length - 1].endWeek)}. Publication after acceptance is additional and is not included.</div>
    </>}
  </div>;
}
