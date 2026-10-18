import { useLocation, useNavigate, Navigate } from 'react-router-dom';
import { useState, useMemo, useEffect } from 'react';
import CompareModal from '../components/CompareModal';
import TimelineBuilder from '../components/TimelineBuilder';
import FilterSidebar from '../components/FilterSidebar';
import ResultRow from '../components/ResultRow';
import Pagination from '../components/Pagination';
import {
  journalKey, rankedJournals, filterJournals, timelineEntry,
  SORT_OPTIONS, sortJournals, emptyFacets, hasActiveFacets, facetCounts, applyFacets, matchesFacets,
} from '../utils/results';
import API from '../api/axios';
import './ResultsV2.css';

const EMPTY_PLANS = {};
const PAGE_SIZES = [10, 20, 30];

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();
  const [downloading, setDownloading] = useState(false);
  const [compareList, setCompareList] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [tab, setTab] = useState('results');
  const [facets, setFacets] = useState(emptyFacets);
  const [limitLowTiers, setLimitLowTiers] = useState(true);
  const [sortKey, setSortKey] = useState('best');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [expanded, setExpanded] = useState(() => new Set());
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selectedJournals, setSelectedJournals] = useState([]);
  const [linkMap, setLinkMap] = useState({});

  const { results, abstract, focus = 'General / Best Fit', minHIndex = 0, minSJR = 0, searchMode, keywords } = location.state || {};
  const { plans = EMPTY_PLANS, stats = {}, warnings = [] } = results || {};

  const allJournals = useMemo(() => rankedJournals(plans), [plans]);
  const numericMatches = useMemo(() => filterJournals(allJournals, minHIndex, minSJR, null), [allJournals, minHIndex, minSJR]);
  const counts = useMemo(() => facetCounts(numericMatches, facets), [numericMatches, facets]);
  const filtered = useMemo(
    () => sortJournals(applyFacets(numericMatches, facets, limitLowTiers), sortKey),
    [numericMatches, facets, limitLowTiers, sortKey]);
  const lowTierHidden = useMemo(
    () => numericMatches.filter(j => matchesFacets(j, facets)).length - applyFacets(numericMatches, facets, true).length,
    [numericMatches, facets]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const currentPage = Math.min(page, pageCount);
  const pageStart = (currentPage - 1) * pageSize;
  const pageJournals = useMemo(() => filtered.slice(pageStart, pageStart + pageSize), [filtered, pageStart, pageSize]);
  useEffect(() => { setPage(1); }, [facets, limitLowTiers, sortKey, pageSize, minHIndex, minSJR, plans]);

  // Resolve homepage links only for the visible page.
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
  const toggleExpanded = key => setExpanded(previous => {
    const next = new Set(previous);
    next.has(key) ? next.delete(key) : next.add(key);
    return next;
  });
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
  const goToPage = n => { setPage(n); window.scrollTo({ top: 0, behavior: 'smooth' }); };

  if (!results) return <Navigate to="/" replace />;

  const totalShowing = filtered.length;
  const showingQ1 = filtered.filter(j => j.quartile === 'Q1').length;
  const showingLowRisk = filtered.filter(j => j.risk_level === 'Low').length;
  const hiddenHighRisk = Math.max(0, (stats.total || 0) - allJournals.length);
  const focusLabel = focus !== 'General / Best Fit' ? focus.split('/')[0].trim() : 'General';
  const isNumericFiltered = minHIndex > 0 || minSJR > 0;
  const filtersActive = hasActiveFacets(facets);
  const clearFacets = () => { setFacets(emptyFacets()); setLimitLowTiers(true); };

  return (
    <div className="rv2">
      {/* ── Summary bar ── */}
      <header className="rv2-summary">
        <div className="rv2-summary-main">
          <h1>{(stats.total || 0).toLocaleString()} journals matched your search</h1>
          <p>
            Ranked by match score · Focus: <strong>{focusLabel}</strong>
            {hiddenHighRisk > 0 && <> · {hiddenHighRisk.toLocaleString()} high-risk journals hidden</>}
          </p>
        </div>
        <dl className="rv2-stats">
          <div><dt>Showing</dt><dd>{totalShowing.toLocaleString()}</dd></div>
          <div><dt>Q1</dt><dd className="is-q1">{showingQ1.toLocaleString()}</dd></div>
          <div><dt>Low risk</dt><dd className="is-low">{showingLowRisk.toLocaleString()}</dd></div>
        </dl>
        <div className="rv2-summary-actions">
          <button type="button" className="rv2-btn rv2-btn--ghost" onClick={() => navigate('/')}>← New search</button>
          <button type="button" className="rv2-btn rv2-btn--primary" onClick={handleDownloadPDF} disabled={downloading}>
            {downloading ? 'Generating…' : 'Download PDF'}
          </button>
        </div>
      </header>

      {warnings?.map((w, i) => <div key={i} className="warning-msg">{w}</div>)}

      {/* ── Tabs ── */}
      <div className="rv2-tabs" role="tablist" aria-label="Results sections">
        <button type="button" role="tab" aria-selected={tab === 'results'} className={tab === 'results' ? 'is-active' : ''}
          onClick={() => setTab('results')}>Results <span className="rv2-tab-count">{totalShowing.toLocaleString()}</span></button>
        <button type="button" role="tab" aria-selected={tab === 'timeline'} className={tab === 'timeline' ? 'is-active' : ''}
          onClick={() => setTab('timeline')}>Timeline planner {selectedJournals.length > 0 && <span className="rv2-tab-count">{selectedJournals.length}</span>}</button>
      </div>

      {/* ── Results tab ── */}
      <section hidden={tab !== 'results'} aria-label="Ranked recommendations">
        <div className="rv2-body">
          <FilterSidebar
            facets={facets} counts={counts} onChange={setFacets} onClear={clearFacets}
            limitLowTiers={limitLowTiers} onLimitChange={setLimitLowTiers}
            open={filtersOpen} onClose={() => setFiltersOpen(false)} lowTierHidden={lowTierHidden} />

          <div className="rv2-main">
            <div className="rv2-toolbar">
              <button type="button" className="rv2-btn rv2-btn--ghost rv2-filters-btn" onClick={() => setFiltersOpen(true)}>
                Filters{filtersActive ? ' •' : ''}
              </button>
              <div className="rv2-range" aria-live="polite">
                {totalShowing ? <>Showing <strong>{pageStart + 1}–{Math.min(pageStart + pageSize, totalShowing)}</strong> of <strong>{totalShowing.toLocaleString()}</strong></> : 'No results'}
              </div>
              <label className="rv2-select">Sort by
                <select value={sortKey} onChange={e => setSortKey(e.target.value)}>
                  {SORT_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
              <label className="rv2-select">Per page
                <select value={pageSize} onChange={e => setPageSize(Number(e.target.value))}>
                  {PAGE_SIZES.map(size => <option key={size} value={size}>{size}</option>)}
                </select>
              </label>
            </div>

            {isNumericFiltered && (
              <div className="rv2-chips">
                <span>Search filters:</span>
                {minHIndex > 0 && <b>H-index ≥ {minHIndex}</b>}
                {minSJR > 0 && <b>SJR ≥ {minSJR}</b>}
                <button type="button" className="rv2-link-btn" onClick={() => navigate('/', { state: { abstract, focus, minHIndex: 0, minSJR: 0 } })}>Change</button>
              </div>
            )}

            <div className="rv2-list">
              {pageJournals.map((journal, index) => {
                const key = journalKey(journal);
                return (
                  <ResultRow
                    key={key}
                    journal={{ ...journal, homepage_url: journal.homepage_url || linkMap[journal.title] }}
                    position={pageStart + index + 1}
                    expanded={expanded.has(key)}
                    onToggle={() => toggleExpanded(key)}
                    inTimeline={selectedJournals.some(j => journalKey(j) === key)}
                    onAddTimeline={() => addToTimeline(journal)}
                    compared={compareList.some(j => journalKey(j) === key)}
                    onCompare={() => handleCompareToggle(journal)}
                  />
                );
              })}
            </div>

            {totalShowing === 0 && (
              <div className="rv2-empty" role="status">
                <p>{filtersActive || isNumericFiltered ? 'No journals match your current filters.' : 'No eligible recommendations were returned for this search.'}</p>
                {filtersActive && <button type="button" className="rv2-btn rv2-btn--ghost" onClick={clearFacets}>Clear filters</button>}
              </div>
            )}

            <Pagination page={currentPage} pageCount={pageCount} onChange={goToPage} />
          </div>
        </div>
      </section>

      {/* ── Timeline tab ── */}
      <section hidden={tab !== 'timeline'} aria-label="Timeline planner">
        <TimelineBuilder active={tab === 'timeline'} journals={selectedJournals} onChange={setSelectedJournals} onAdd={addToTimeline} onGoToResults={() => setTab('results')} />
      </section>

      <footer className="rv2-disclaimers">
        <p>These recommendations are AI-generated. Always verify journal scope before submitting.</p>
        <p>APC values from DOAJ — confirm on the journal website. Time to publish is sourced from DOAJ and is AI-assisted; actual timelines may differ significantly.</p>
      </footer>

      {compareList.length > 0 && (
        <div className="compare-bar">
          <div className="compare-bar-avatars">
            {compareList.map((j, i) => <div key={i} className="compare-avatar" title={j.title}>{j.title[0]}</div>)}
          </div>
          <div className="compare-bar-count"><strong>{compareList.length}</strong> selected</div>
          <button className="compare-bar-btn" onClick={() => setShowModal(true)}>Compare now</button>
          <button className="compare-bar-close" onClick={() => setCompareList([])} aria-label="Clear comparison">✕</button>
        </div>
      )}
      {showModal && <CompareModal journals={compareList} onClose={() => setShowModal(false)} />}
    </div>
  );
}
