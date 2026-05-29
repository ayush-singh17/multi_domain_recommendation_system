import { useLocation, useNavigate } from 'react-router-dom';
import { useState, useMemo } from 'react';
import PlanSection from '../components/PlanSection';
import CompareModal from '../components/CompareModal';
import SubmissionTimeline from '../components/SubmissionTimeline';
import API from '../api/axios';

// ── Mirrors timeline_calculator.py — runs entirely in the browser ─────────────
const QUARTILE_FALLBACK = { Q1: 20, Q2: 16, Q3: 12, Q4: 10, Unranked: 10 };
const REVISION_WEEKS    = 2;

function getReviewWeeks(journal) {
  const raw = journal?.weeks_to_publish;
  if (raw != null && raw !== '' && raw !== 'None') {
    const n = parseFloat(raw);
    if (!isNaN(n)) return [Math.round(n), false];
  }
  const q = journal?.quartile ?? 'Q2';
  return [QUARTILE_FALLBACK[q] ?? 16, true];
}

function weeksToDisplay(weeks) {
  const months = Math.round((weeks / 4.33) * 10) / 10;
  return `~${weeks} weeks (~${months} months)`;
}

function buildDynamicTimeline(filteredPlans) {
  const per_plan = {};

  for (const key of ['A', 'B', 'C']) {
    const journals = filteredPlans[key] || [];
    if (journals.length === 0) { per_plan[key] = null; continue; }
    const top = journals[0];
    const [weeks, estimated] = getReviewWeeks(top);
    per_plan[key] = {
      title:        top.title ?? '',
      quartile:     top.quartile ?? '',
      weeks,
      is_estimated: estimated,
      display:      weeksToDisplay(weeks),
      source:       estimated ? 'Estimated from quartile avg.' : 'DOAJ publisher data',
    };
  }

  const a = per_plan.A, b = per_plan.B, c = per_plan.C;
  const scenarios = {};

  if (a) {
    scenarios.optimistic = {
      label:   'Optimistic',
      desc:    `Accepted at ${a.title.slice(0, 40)}${a.title.length > 40 ? '…' : ''}`,
      weeks:   a.weeks,
      display: weeksToDisplay(a.weeks),
      steps: [
        { plan: 'A', action: 'Submit', journal: a.title, weeks: a.weeks },
      ],
    };
  }

  if (a && b) {
    const total = a.weeks + REVISION_WEEKS + b.weeks;
    scenarios.realistic = {
      label:   'Realistic',
      desc:    `Rejected at A → accepted at ${b.title.slice(0, 40)}${b.title.length > 40 ? '…' : ''}`,
      weeks:   total,
      display: weeksToDisplay(total),
      steps: [
        { plan: 'A', action: 'Submit', journal: a.title, weeks: a.weeks },
        { plan: '',  action: 'Revise', journal: 'Revise & reformat paper', weeks: REVISION_WEEKS },
        { plan: 'B', action: 'Submit', journal: b.title, weeks: b.weeks },
      ],
    };
  }

  if (a && b && c) {
    const total = a.weeks + REVISION_WEEKS + b.weeks + REVISION_WEEKS + c.weeks;
    scenarios.worst_case = {
      label:   'Worst Case',
      desc:    `Rejected at A and B → accepted at ${c.title.slice(0, 40)}${c.title.length > 40 ? '…' : ''}`,
      weeks:   total,
      display: weeksToDisplay(total),
      steps: [
        { plan: 'A', action: 'Submit', journal: a.title, weeks: a.weeks },
        { plan: '',  action: 'Revise', journal: 'Revise & reformat paper', weeks: REVISION_WEEKS },
        { plan: 'B', action: 'Submit', journal: b.title, weeks: b.weeks },
        { plan: '',  action: 'Revise', journal: 'Revise & reformat paper', weeks: REVISION_WEEKS },
        { plan: 'C', action: 'Submit', journal: c.title, weeks: c.weeks },
      ],
    };
  }

  let advice;
  if (a && b) {
    const optW  = scenarios.optimistic?.weeks ?? 0;
    const realW = scenarios.realistic?.weeks  ?? 0;
    advice = `Start with Plan A. If accepted, you'll be published in ${weeksToDisplay(optW)}. ` +
             `If rejected, expect the full process to take ${weeksToDisplay(realW)} through Plan B. ` +
             `Use the rejection feedback to strengthen your paper before resubmitting.`;
  } else if (a) {
    advice = `Submit to Plan A. Expected review time: ${a.display}.`;
  } else if (b) {
    advice = `Only Plan B journals are visible with the current filters. Expected review time: ${b.display}.`;
  } else if (c) {
    advice = `Only Plan C journals are visible with the current filters. Expected review time: ${c.display}.`;
  } else {
    advice = null; // signal: no journals visible at all
  }

  return { per_plan, scenarios, advice };
}
// ─────────────────────────────────────────────────────────────────────────────

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();

  const [downloading, setDownloading] = useState(false);
  const [compareList, setCompareList] = useState([]);
  const [showModal, setShowModal]     = useState(false);
  const [activeTag, setActiveTag]     = useState(null);

  const { results, abstract, focus, minHIndex = 0, minSJR = 0 } = location.state || {};
  const { plans = {}, stats = {}, warnings = [] } = results || {};

  // Apply filters (H-index, SJR, and active tag) to all three plans
  const filteredPlans = useMemo(() => {
    const apply = (journals) => {
      if (!journals) return [];
      return journals.filter(j => {
        const hOk   = minHIndex === 0 || (j.h_index != null && parseFloat(j.h_index) >= minHIndex);
        const sjrOk = minSJR   === 0 || (j.sjr     != null && parseFloat(j.sjr)      >= minSJR);
        let tagOk   = true;
        if (activeTag) {
          if (['Q1','Q2','Q3','Q4'].includes(activeTag)) {
            tagOk = j.quartile === activeTag;
          } else if (activeTag === 'Low Risk') {
            tagOk = j.risk_level === 'Low';
          } else if (activeTag === 'Medium Risk') {
            tagOk = j.risk_level === 'Medium';
          }
        }
        return hOk && sjrOk && tagOk;
      });
    };
    return { A: apply(plans.A), B: apply(plans.B), C: apply(plans.C) };
  }, [plans, minHIndex, minSJR, activeTag]);

  // ── Dynamic timeline recomputed from whatever journals are currently visible ──
  const dynamicTimeline = useMemo(() => buildDynamicTimeline(filteredPlans), [filteredPlans]);

  // Count matching journals per tag across all plans (before tag filter, after other filters)
  const tagCounts = useMemo(() => {
    const allRaw = [...(plans.A || []), ...(plans.B || []), ...(plans.C || [])].filter(j => {
      const hOk   = minHIndex === 0 || (j.h_index != null && parseFloat(j.h_index) >= minHIndex);
      const sjrOk = minSJR   === 0 || (j.sjr     != null && parseFloat(j.sjr)      >= minSJR);
      return hOk && sjrOk;
    });
    const count = (fn) => allRaw.filter(fn).length;
    return {
      'Q1':          count(j => j.quartile   === 'Q1'),
      'Q2':          count(j => j.quartile   === 'Q2'),
      'Q3':          count(j => j.quartile   === 'Q3'),
      'Q4':          count(j => j.quartile   === 'Q4'),
      'Low Risk':    count(j => j.risk_level === 'Low'),
      'Medium Risk': count(j => j.risk_level === 'Medium'),
    };
  }, [plans, minHIndex, minSJR]);

  // Early return AFTER all hooks
  if (!results) { navigate('/'); return null; }

  const totalAll     = (plans.A?.length || 0) + (plans.B?.length || 0) + (plans.C?.length || 0);
  const totalShowing = filteredPlans.A.length + filteredPlans.B.length + filteredPlans.C.length;
  const hiddenCount  = totalAll - totalShowing;
  const isFiltered   = minHIndex > 0 || minSJR > 0;

  const handleCompareToggle = (j) => {
    setCompareList(prev => {
      const exists = prev.find(x => x.issn === j.issn);
      if (exists) return prev.filter(x => x.issn !== j.issn);
      if (prev.length >= 3) { alert('Max 3 journals for comparison.'); return prev; }
      return [...prev, j];
    });
  };

  const handleDownloadPDF = async () => {
    setDownloading(true);
    try {
      const res = await API.post('/search/recommend/pdf/', { abstract, focus }, { responseType: 'blob' });
      const url  = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url; link.download = 'journal_recommendations.pdf'; link.click();
      window.URL.revokeObjectURL(url);
    } catch { alert('PDF generation failed.'); }
    finally { setDownloading(false); }
  };

  return (
    <div className="results-container">

      {/* Stats */}
      <div className="results-stats">
        <div className="stat-card">
          <div className="stat-card-num">{stats.total}</div>
          <div className="stat-card-label">Total Matches</div>
        </div>
        <div className="stat-card accent-indigo">
          <div className="stat-card-num">{stats.q1_count}</div>
          <div className="stat-card-label">Q1 Journals</div>
        </div>
        <div className="stat-card accent-emerald">
          <div className="stat-card-num">{stats.low_risk}</div>
          <div className="stat-card-label">Low Risk</div>
        </div>
        <div className="stat-card accent-amber">
          <div className="stat-card-num">{focus !== 'General / Best Fit' ? focus.split('/')[0].trim() : 'General'}</div>
          <div className="stat-card-label">Focus Mode</div>
        </div>
      </div>

      {warnings?.map((w, i) => <div key={i} className="warning-msg">{w}</div>)}

      {/* ── Tag filter tabs ── */}
      <div className="tag-filter-bar">
        <span className="tag-filter-label">Filter</span>
        {[['Q1','tag-q1'],['Q2','tag-q2'],['Q3','tag-q3'],['Q4','tag-q4'],['Low Risk','tag-risk-low'],['Medium Risk','tag-risk-med']].map(([tag, cls]) => (
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

      {/* ── Dynamic roadmap — reacts to every filter change ── */}
      <SubmissionTimeline timeline={dynamicTimeline} totalShowing={totalShowing} />

      <PlanSection plan="A" journals={filteredPlans.A} onCompareToggle={handleCompareToggle} compareList={compareList} />
      <PlanSection plan="B" journals={filteredPlans.B} onCompareToggle={handleCompareToggle} compareList={compareList} />
      <PlanSection plan="C" journals={filteredPlans.C} onCompareToggle={handleCompareToggle} compareList={compareList} />

      {/* No results after filtering */}
      {totalShowing === 0 && (activeTag || isFiltered) && (
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
