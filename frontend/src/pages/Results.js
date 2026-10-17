import { useLocation, useNavigate, Navigate } from 'react-router-dom';
import { useState, useMemo, useEffect } from 'react';
import JournalCard from '../components/JournalCard';
import CompareModal from '../components/CompareModal';
import TimelineBuilder from '../components/TimelineBuilder';
import { journalKey, rankedJournals, filterJournals, capDefaultMix, timelineEntry } from '../utils/results';
import API from '../api/axios';
import './ResultsWorkspace.css';

const EMPTY_PLANS = {};
const TAGS = [['Q1','tag-q1'],['Q2','tag-q2'],['Q3','tag-q3'],['Q4','tag-q4'],['Low Risk','tag-risk-low'],['Medium Risk','tag-risk-med'],['MAHE Approved','tag-mahe']];

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();
  const [downloading, setDownloading] = useState(false);
  const [compareList, setCompareList] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [activeTag, setActiveTag] = useState(null);
  const [tab, setTab] = useState('results');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selectedJournals, setSelectedJournals] = useState([]);
  const [linkMap, setLinkMap] = useState({});
  const { results, abstract, focus = 'General / Best Fit', minHIndex = 0, minSJR = 0, searchMode, keywords } = location.state || {};
  const { plans = EMPTY_PLANS, stats = {}, warnings = [] } = results || {};
  const allJournals = useMemo(() => rankedJournals(plans), [plans]);
  const numericMatches = useMemo(() => filterJournals(allJournals, minHIndex, minSJR, null), [allJournals, minHIndex, minSJR]);
  const filteredJournals = useMemo(() => activeTag
    ? filterJournals(numericMatches, 0, 0, activeTag)
    : capDefaultMix(numericMatches), [numericMatches, activeTag]);
  const tagCounts = useMemo(() => Object.fromEntries(TAGS.map(([tag]) => [tag, filterJournals(numericMatches, 0, 0, tag).length])), [numericMatches]);
  const pageCount = Math.max(1, Math.ceil(filteredJournals.length / pageSize));
  const currentPage = Math.min(page, pageCount);
  const pageStart = (currentPage - 1) * pageSize;
  const pageJournals = useMemo(() => filteredJournals.slice(pageStart, pageStart + pageSize), [filteredJournals, pageStart, pageSize]);
  useEffect(() => { setPage(1); }, [activeTag, minHIndex, minSJR, pageSize, plans]);

  // Resolve links only for the visible page, instead of blocking on hundreds of lookups.
  useEffect(() => {
    if (tab !== 'results') return;
    const titles = pageJournals.filter(j => !j.homepage_url && !(j.title in linkMap)).map(j => j.title);
    if (!titles.length) return;
    const controller = new AbortController();
    API.post('/search/journal-links/', { titles }, { signal: controller.signal })
      .then(({ data }) => setLinkMap(previous => ({ ...previous, ...data.links })))
      .catch(() => {
        if (!controller.signal.aborted) setLinkMap(previous => ({ ...previous, ...Object.fromEntries(titles.map(t => [t, null])) }));
      });
    return () => controller.abort();
  }, [pageJournals, tab, linkMap]);

  const addToTimeline = journal => setSelectedJournals(previous =>
    previous.some(j => journalKey(j) === journalKey(journal)) ? previous : [...previous, timelineEntry(journal)]);
  const showingQ1 = filteredJournals.filter(j => j.quartile === 'Q1').length;
  const showingLowRisk = filteredJournals.filter(j => j.risk_level === 'Low').length;
  const totalAll = allJournals.length;
  const totalShowing = filteredJournals.length;
  const hiddenCount = totalAll - totalShowing;
  const isFiltered = minHIndex > 0 || minSJR > 0;
  const handleCompareToggle = journal => setCompareList(previous => {
    if (previous.some(j => journalKey(j) === journalKey(journal))) return previous.filter(j => journalKey(j) !== journalKey(journal));
    if (previous.length >= 3) { alert('Max 3 journals for comparison.'); return previous; }
    return [...previous, journal];
  });
  const handleDownloadPDF = async () => {
    setDownloading(true);
    try {
      const res = await API.post('/search/recommend/pdf/', { abstract, focus, search_mode: searchMode || 'abstract', keywords: keywords || [] }, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url; link.download = 'journal_recommendations.pdf'; link.click();
      window.URL.revokeObjectURL(url);
    } catch { alert('PDF generation failed.'); }
    finally { setDownloading(false); }
  };
  if (!results) return <Navigate to="/" replace />;

  return (
    <div className="results-container">

      {/* Stats */}
      <div className="results-stats">
        <div className="stat-card">
          <div className="stat-card-num">{stats.total || 0}</div>
          <div className="stat-card-label">Database Matches</div>
        </div>
        <div className="stat-card accent-indigo">
          <div className="stat-card-num">{totalShowing}</div>
          <div className="stat-card-label">Recommended Options</div>
        </div>
        <div className="stat-card accent-amber">
          <div className="stat-card-num">{showingQ1}</div>
          <div className="stat-card-label">Q1 Recommended</div>
        </div>
        <div className="stat-card accent-emerald">
          <div className="stat-card-num">{showingLowRisk}</div>
          <div className="stat-card-label">Low Risk Recommended</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-num">{focus !== 'General / Best Fit' ? focus.split('/')[0].trim() : 'General'}</div>
          <div className="stat-card-label">Focus Mode</div>
        </div>
      </div>

      {warnings?.map((w, i) => <div key={i} className="warning-msg">{w}</div>)}

      {/* ── Tag filter tabs ── */}
      <div className="tag-filter-bar">
        <span className="tag-filter-label">Filter</span>
        {[['Q1','tag-q1'],['Q2','tag-q2'],['Q3','tag-q3'],['Q4','tag-q4'],['Low Risk','tag-risk-low'],['Medium Risk','tag-risk-med'],['MAHE Approved','tag-mahe']].map(([tag, cls]) => (
          <button
            key={tag}
            className={'tag-filter-chip ' + cls + (activeTag === tag ? ' active' : '')}
            onClick={() => setActiveTag(prev => prev === tag ? null : tag)}
          >
            {tag}
            {tagCounts[tag] > 0 && <span className="tag-filter-count">{tagCounts[tag]}</span>}
          </button>
        ))}
        {activeTag && (
          <button className="tag-filter-clear" onClick={() => setActiveTag(null)}>✕ Clear</button>
        )}
      </div>

      {/* Show active numeric filters as read-only badges */}
      {isFiltered && (
        <div className="results-filter-bar">
          <div className="filter-bar-label">
            <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
              <path d="M1 2h12M3 7h8M5 12h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
            </svg>
            Active Filters
          </div>
          {minHIndex > 0 && (
            <div className="filter-input-group">
              <span className="filter-input-label">H-index ≥</span>
              <span style={{fontFamily:'var(--font-mono)',fontSize:'.85rem',fontWeight:700,color:'var(--primary)'}}>{minHIndex}</span>
            </div>
          )}
          {minSJR > 0 && (
            <div className="filter-input-group">
              <span className="filter-input-label">SJR ≥</span>
              <span style={{fontFamily:'var(--font-mono)',fontSize:'.85rem',fontWeight:700,color:'var(--primary)'}}>{minSJR}</span>
            </div>
          )}
          <div className="filter-bar-summary">
            <strong>{totalShowing}</strong> of {totalAll} journals shown
            {hiddenCount > 0 && <span style={{color:'var(--text-3)'}}>· {hiddenCount} hidden</span>}
          </div>
          <button className="filter-reset" onClick={() => navigate('/', { state: { abstract, focus, minHIndex: 0, minSJR: 0 } })}>
            ✕ Change Filters
          </button>
        </div>
      )}

      <nav className="results-subnav" aria-label="Results sections">
        <button type="button" aria-current={tab === 'results' ? 'page' : undefined} onClick={() => setTab('results')}>Results ({totalShowing})</button>
        <button type="button" aria-current={tab === 'timeline' ? 'page' : undefined} onClick={() => setTab('timeline')}>Timeline Calculator{selectedJournals.length ? ` (${selectedJournals.length})` : ''}</button>
      </nav>

      <section hidden={tab !== 'results'} aria-label="Ranked recommendations">
        {!activeTag && <p className="timeline-search-status">The default mix includes up to 2 Q3 and 2 Q4 journals. Select a quartile filter to see all its matches.</p>}
        <div className="results-page-toolbar">
          <div aria-live="polite">Showing <strong>{totalShowing ? pageStart + 1 : 0}–{Math.min(pageStart + pageSize, totalShowing)}</strong> of {totalShowing} matching recommendations · Highest score first</div>
          <label>Per page <select value={pageSize} onChange={e => setPageSize(Number(e.target.value))}>{[10, 20, 30].map(size => <option key={size} value={size}>{size}</option>)}</select></label>
        </div>
        <div className="plan-journals">
          {pageJournals.map((journal, index) => {
            const key = journalKey(journal);
            const added = selectedJournals.some(j => journalKey(j) === key);
            const displayed = { ...journal, homepage_url: journal.homepage_url || linkMap[journal.title] };
            return <div key={key} className="ranked-result">
              <div className="ranked-result-toolbar"><span>Match #{pageStart + index + 1}</span><button type="button" className="btn-secondary" disabled={added} onClick={() => addToTimeline(journal)}>{added ? 'Added to timeline' : '+ Add to timeline'}</button></div>
              <JournalCard journal={displayed} planKey={journal._plan} onCompareToggle={handleCompareToggle} isCompared={compareList.some(j => journalKey(j) === key)} />
            </div>;
          })}
        </div>
        {totalShowing > 0 && <nav className="results-pagination" aria-label="Result pages">
          <button type="button" disabled={currentPage === 1} onClick={() => setPage(1)}>First</button>
          <button type="button" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>Previous</button>
          <label>Page <select aria-label="Page number" value={currentPage} onChange={e => setPage(Number(e.target.value))}>{Array.from({ length: pageCount }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}</select> of {pageCount}</label>
          <button type="button" disabled={currentPage === pageCount} onClick={() => setPage(currentPage + 1)}>Next</button>
          <button type="button" disabled={currentPage === pageCount} onClick={() => setPage(pageCount)}>Last</button>
        </nav>}
        {!totalShowing && !activeTag && !isFiltered && <p role="status">No eligible recommendations were returned for this search.</p>}
      </section>
      <section hidden={tab !== 'timeline'} aria-label="Timeline calculator">
        <TimelineBuilder active={tab === 'timeline'} journals={selectedJournals} onChange={setSelectedJournals} onAdd={addToTimeline} />
      </section>

      {/* No results after filtering */}
      {tab === 'results' && totalShowing === 0 && (activeTag || isFiltered) && (
        <div style={{textAlign:'center', padding:'3rem 2rem', color:'var(--text-3)'}}>
          <div style={{fontSize:'1.5rem', marginBottom:'.75rem', opacity:.35}}>◎</div>
          <p style={{marginBottom:'1.25rem', fontSize:'.9rem'}}>No journals match your current filters.</p>
          <button className="btn-secondary" onClick={() => {
            setActiveTag(null);
            navigate(location.pathname, { state: { ...location.state, minHIndex: 0, minSJR: 0 }, replace: true });
          }}>
            Reset Filters
          </button>
        </div>
      )}

      <div className="results-actions">
        <button className="btn-secondary" onClick={() => navigate('/')}>← New Search</button>
        <button className="btn-primary" onClick={handleDownloadPDF} disabled={downloading} style={{width:'auto', marginTop:0}}>
          {downloading ? 'Generating PDF...' : 'Download PDF Report'}
        </button>
      </div>

      <div className="disclaimer">These recommendations are AI-generated. Always verify journal scope before submitting.</div>
      <div className="disclaimer">APC values from DOAJ — confirm on the journal website before submitting.</div>
      <div className="disclaimer">Time to publish is sourced from DOAJ and is AI-assisted — actual timelines may differ significantly.</div>

      {compareList.length > 0 && (
        <div className="compare-bar">
          <div className="compare-bar-avatars">
            {compareList.map((j, i) => (
              <div key={i} className="compare-avatar" title={j.title}>{j.title[0]}</div>
            ))}
          </div>
          <div className="compare-bar-count"><strong>{compareList.length}</strong> journals selected</div>
          <button className="compare-bar-btn" onClick={() => setShowModal(true)}>Compare Now</button>
          <button className="compare-bar-close" onClick={() => setCompareList([])}>✕</button>
        </div>
      )}

      {showModal && <CompareModal journals={compareList} onClose={() => setShowModal(false)} />}
    </div>
  );
}
