import { useState, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import API from '../api/axios';

const FOCUS_OPTIONS = [
  'General / Best Fit',
  'Ethics / Philosophy',
  'Clinical Impact',
  'Legal / Policy',
  'Technical / Engineering',
  'Cross-disciplinary Science',
];

const ABSTRACT_LOADING_STEPS = [
  'Scanning 29,553 indexed journals...',
  'Running BERT semantic analysis...',
  'Computing hybrid relevance scores...',
  'Assessing journal credibility...',
  'Building 3-tier submission strategy...',
];

const KEYWORD_LOADING_STEPS = [
  'Expanding keywords into semantic context...',
  'Scanning 29,553 indexed journals...',
  'Running BERT semantic analysis...',
  'Computing hybrid relevance scores...',
  'Building 3-tier submission strategy...',
];

const MAX_KEYWORDS = 10;

// ── Tooltip component ────────────────────────────────────────────────────────
// Pure CSS-driven — no portal, no JS positioning, no library.
// Placement: 'top' (default) | 'bottom' | 'left' | 'right'
function Tooltip({ text, placement = 'top', children, maxWidth = 220, className = '', style = {} }) {
  return (
    <span className={`tooltip-wrap tooltip-${placement} ${className}`} style={style}>
      {children}
      <span className="tooltip-bubble" style={{ maxWidth }}>
        {text}
      </span>
    </span>
  );
}

// ── Info icon with tooltip (for labels) ──────────────────────────────────────
function InfoTip({ text, placement = 'top' }) {
  return (
    <Tooltip text={text} placement={placement}>
      <span className="info-tip-icon" aria-label="More info" tabIndex={0}>
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.4" opacity=".5"/>
          <path d="M8 7v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          <circle cx="8" cy="5" r=".8" fill="currentColor"/>
        </svg>
      </span>
    </Tooltip>
  );
}

// ── Neural-network SVG (right column) ────────────────────────────────────────
function NeuralViz() {
  const nodes = [
    { cx: 280, cy: 120 }, { cx: 380, cy: 80  }, { cx: 460, cy: 160 },
    { cx: 340, cy: 220 }, { cx: 420, cy: 280 }, { cx: 260, cy: 290 },
    { cx: 480, cy: 340 }, { cx: 360, cy: 360 },
  ];
  const edges = [
    [0,1],[1,2],[2,3],[3,4],[4,5],[5,0],[2,4],[1,3],[3,5],[4,7],[6,7],[5,6]
  ];
  return (
    <svg viewBox="0 0 560 460" style={{width:'100%',height:'100%',opacity:.7}} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="nodeGrad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#7c8cff" stopOpacity=".9"/>
          <stop offset="100%" stopColor="#7c8cff" stopOpacity=".2"/>
        </radialGradient>
        <radialGradient id="nodeGreen" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#3ddc97" stopOpacity=".9"/>
          <stop offset="100%" stopColor="#3ddc97" stopOpacity=".2"/>
        </radialGradient>
      </defs>
      {edges.map(([a,b],i) => (
        <line key={i}
          x1={nodes[a].cx} y1={nodes[a].cy}
          x2={nodes[b].cx} y2={nodes[b].cy}
          stroke="rgba(124,140,255,0.18)" strokeWidth="1"
        />
      ))}
      {nodes.map((n, i) => (
        <g key={i}>
          <circle cx={n.cx} cy={n.cy} r={i === 4 ? 18 : 8}
            fill={i === 4 ? 'url(#nodeGreen)' : 'url(#nodeGrad)'}
            style={{animation:`nodesPulse ${2 + i*0.3}s ease-in-out infinite`}}
          />
          {i === 4 && (
            <circle cx={n.cx} cy={n.cy} r={26}
              fill="none" stroke="rgba(61,220,151,0.2)" strokeWidth="1"
            />
          )}
        </g>
      ))}
    </svg>
  );
}

// ── Keyword chip tag-input ───────────────────────────────────────────────────
function KeywordInput({ keywords, setKeywords, disabled }) {
  const [inputVal, setInputVal] = useState('');
  const inputRef = useRef(null);

  const addKeyword = useCallback((raw) => {
    const trimmed = raw.trim().replace(/,+$/, '').trim();
    if (!trimmed) return;
    if (keywords.length >= MAX_KEYWORDS) return;
    if (keywords.some(k => k.toLowerCase() === trimmed.toLowerCase())) return;
    setKeywords(prev => [...prev, trimmed]);
  }, [keywords, setKeywords]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addKeyword(inputVal);
      setInputVal('');
    } else if (e.key === 'Backspace' && inputVal === '' && keywords.length > 0) {
      setKeywords(prev => prev.slice(0, -1));
    }
  };

  const handleChange = (e) => {
    const val = e.target.value;
    if (val.includes(',')) {
      const parts = val.split(',');
      parts.slice(0, -1).forEach(p => addKeyword(p));
      setInputVal(parts[parts.length - 1]);
    } else {
      setInputVal(val);
    }
  };

  const removeKeyword = (idx) => {
    setKeywords(prev => prev.filter((_, i) => i !== idx));
  };

  return (
    <div
      className={'keyword-input-area' + (disabled ? ' disabled' : '')}
      onClick={() => !disabled && inputRef.current?.focus()}
    >
      {keywords.map((kw, idx) => (
        <span key={idx} className="keyword-chip">
          {kw}
          {!disabled && (
            <button
              type="button"
              className="keyword-chip-delete"
              onClick={e => { e.stopPropagation(); removeKeyword(idx); }}
              aria-label={`Remove ${kw}`}
            >×</button>
          )}
        </span>
      ))}
      {keywords.length < MAX_KEYWORDS && (
        <input
          ref={inputRef}
          type="text"
          className="keyword-chip-input"
          value={inputVal}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={keywords.length === 0 ? 'Type a keyword and press Enter or comma…' : 'Add another…'}
          disabled={disabled}
        />
      )}
    </div>
  );
}

// ── Stat strip tooltip content ────────────────────────────────────────────────
const STAT_TIPS = {
  'Indexed Journals': 'Our database covers 29,553 peer-reviewed journals from Scopus, DOAJ, and SciMago across all disciplines.',
  'Strategy Plans':   'Results are split into 3 tiers — Plan A (ambitious Q1), Plan B (balanced Q2), Plan C (safe fallback) — giving you a full submission strategy.',
  'Semantic Matching':'We use BERT (Bidirectional Encoder Representations from Transformers) to understand the meaning of your text, not just individual keywords.',
  'Quartile Coverage':'Every journal is ranked Q1–Q4 by SciMago based on its citation impact relative to others in the same field.',
};

// ── Main Search component ────────────────────────────────────────────────────
export default function Search() {
  const navigate = useNavigate();
  const location = useLocation();
  const prefill  = location.state || {};

  const [searchMode, setSearchMode] = useState(prefill.searchMode || 'abstract');
  const [abstract, setAbstract]     = useState(prefill.abstract  || '');
  const [keywords, setKeywords]     = useState(prefill.keywords  || []);
  const [focus, setFocus]           = useState(prefill.focus     || 'General / Best Fit');
  const [minHIndex, setMinHIndex]   = useState(prefill.minHIndex || 0);
  const [minSJR, setMinSJR]         = useState(prefill.minSJR    || 0);
  const [loading, setLoading]       = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [error, setError]           = useState('');

  const wordCount    = abstract.trim().split(/\s+/).filter(Boolean).length;
  const loadingSteps = searchMode === 'keyword' ? KEYWORD_LOADING_STEPS : ABSTRACT_LOADING_STEPS;
  const isSubmittable = searchMode === 'abstract'
    ? abstract.trim().length > 0
    : keywords.length > 0;

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!isSubmittable) return;
    setError(''); setLoading(true); setLoadingStep(0);
    const interval = setInterval(() => setLoadingStep(p => (p + 1) % loadingSteps.length), 2200);
    try {
      const payload = {
        focus,
        search_mode: searchMode,
        abstract:    searchMode === 'abstract' ? abstract : '',
        keywords:    searchMode === 'keyword'  ? keywords : [],
      };
      const res = await API.post('/search/recommend/', payload);
      clearInterval(interval);
      navigate('/results', {
        state: {
          results:   res.data,
          abstract:  searchMode === 'abstract' ? abstract : keywords.join(', '),
          focus,
          minHIndex,
          minSJR,
          searchMode,
          keywords,
        }
      });
    } catch (err) {
      clearInterval(interval);
      if (err.response?.status === 503) setError('ML service is not running. Start it first.');
      else setError('Something went wrong. Please try again.');
    } finally { setLoading(false); }
  };

  return (
    <div className="search-page">

      {/* ── Left column ── */}
      <div className="search-left">
        <div className="hero-eyebrow animate-fade-up">Neural-Powered Academic Intelligence</div>

        <h1 className="hero-title animate-fade-up-1">
          Find the <em>Right<br />Journal</em> for Your<br />Research
        </h1>

        <p className="hero-sub animate-fade-up-2">
          Leverage our neural-mapping engine to discover journals that align
          with your manuscript's semantic fingerprint, impact goals, and submission timeline.
        </p>

        <form onSubmit={handleSearch} className="animate-fade-up-2">
          <div className="search-panel">

            {/* ── Mode tab switcher ── */}
            <div className="search-mode-tabs">
              <Tooltip
                text="Paste your full manuscript abstract for the deepest semantic matching. BERT reads meaning, not just keywords."
                placement="bottom"
              >
                <button
                  type="button"
                  id="tab-abstract"
                  className={'search-mode-tab' + (searchMode === 'abstract' ? ' active' : '')}
                  onClick={() => { setSearchMode('abstract'); setError(''); }}
                  disabled={loading}
                >
                  <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                    <rect x="1" y="2" width="14" height="2" rx="1" fill="currentColor" opacity=".7"/>
                    <rect x="1" y="6" width="10" height="2" rx="1" fill="currentColor"/>
                    <rect x="1" y="10" width="12" height="2" rx="1" fill="currentColor" opacity=".7"/>
                    <rect x="1" y="14" width="7" height="2" rx="1" fill="currentColor" opacity=".4"/>
                  </svg>
                  Abstract
                </button>
              </Tooltip>

              <Tooltip
                text="Type individual research topics — they're automatically expanded into semantic context before ranking journals."
                placement="bottom"
              >
                <button
                  type="button"
                  id="tab-keywords"
                  className={'search-mode-tab' + (searchMode === 'keyword' ? ' active' : '')}
                  onClick={() => { setSearchMode('keyword'); setError(''); }}
                  disabled={loading}
                >
                  <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                    <rect x="1" y="3" width="6" height="4" rx="2" fill="currentColor" opacity=".85"/>
                    <rect x="9" y="3" width="6" height="4" rx="2" fill="currentColor" opacity=".85"/>
                    <rect x="1" y="9" width="6" height="4" rx="2" fill="currentColor" opacity=".5"/>
                    <rect x="9" y="9" width="6" height="4" rx="2" fill="currentColor" opacity=".5"/>
                  </svg>
                  Keywords
                </button>
              </Tooltip>
            </div>

            {/* ── Abstract mode ── */}
            {searchMode === 'abstract' && (
              <>
                <div className="abstract-label">
                  <span style={{ display: 'flex', alignItems: 'center', gap: '.4rem' }}>
                    Manuscript Abstract
                    <InfoTip
                      text="Paste your research abstract (100–250 words). The BERT model reads the full semantic meaning — more context gives significantly better journal matches."
                      placement="right"
                    />
                  </span>
                  {abstract.trim()
                    ? <span className="abstract-label-status">Neural Analysis Active</span>
                    : <span style={{fontSize:'.65rem',color:'var(--text-3)',fontWeight:400,letterSpacing:'.02em',textTransform:'none'}}>Recommended: 100–250 words</span>
                  }
                </div>

                <Tooltip
                  text="Aim for 100–250 words. The system uses BERT's 512-token window — longer abstracts are truncated. Short text gives weaker results."
                  placement="right"
                  maxWidth={260}
                  className="w-full"
                >
                  <textarea
                    className="abstract-input"
                    value={abstract}
                    onChange={e => setAbstract(e.target.value)}
                    placeholder="Paste your research abstract here for semantic analysis..."
                    rows={7}
                    disabled={loading}
                  />
                </Tooltip>

                {/* Word count bar */}
                {abstract.trim() && (() => {
                  const ideal = 150;
                  const pct   = Math.min(100, Math.round((wordCount / ideal) * 100));
                  const color = wordCount < 30  ? 'var(--danger)'
                              : wordCount < 80  ? 'var(--tertiary)'
                              : wordCount <= 250 ? 'var(--secondary)'
                              : 'var(--primary)';
                  const msg   = wordCount < 30  ? `Too short (${wordCount} words) — BERT needs at least 30`
                              : wordCount < 80  ? `Short (${wordCount} words) — more context improves accuracy`
                              : wordCount <= 250 ? `Good length (${wordCount} words) — optimal for BERT`
                              : `Long (${wordCount} words) — BERT will use the first 512 tokens`;
                  return (
                    <div style={{marginTop:'.6rem'}}>
                      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'.3rem'}}>
                        <span style={{fontSize:'.68rem',color,fontWeight:600}}>{msg}</span>
                        <span style={{fontSize:'.65rem',color:'var(--text-3)',fontFamily:'var(--font-mono)'}}>{wordCount} / 250</span>
                      </div>
                      <div style={{background:'var(--surface-3)',borderRadius:3,height:3,overflow:'hidden'}}>
                        <div style={{width:pct+'%',height:'100%',background:color,borderRadius:3,transition:'width .3s, background .3s'}} />
                      </div>
                    </div>
                  );
                })()}
              </>
            )}

            {/* ── Keyword mode ── */}
            {searchMode === 'keyword' && (
              <>
                <div className="abstract-label">
                  <span style={{ display: 'flex', alignItems: 'center', gap: '.4rem' }}>
                    Research Keywords
                    <InfoTip
                      text="Add up to 10 keywords describing your research topic. They'll be expanded into a full semantic sentence before being matched against all 29,553 journals."
                      placement="right"
                    />
                  </span>
                  {keywords.length > 0
                    ? <span className="abstract-label-status">{keywords.length} / {MAX_KEYWORDS} keywords</span>
                    : <span style={{fontSize:'.65rem',color:'var(--text-3)',fontWeight:400,letterSpacing:'.02em',textTransform:'none'}}>Press Enter or comma to add each keyword</span>
                  }
                </div>

                <Tooltip
                  text="Press Enter or comma after each keyword. Paste a comma-separated list to add all at once. Backspace removes the last chip. Duplicates are ignored."
                  placement="right"
                  maxWidth={270}
                  className="w-full"
                >
                  <KeywordInput
                    keywords={keywords}
                    setKeywords={setKeywords}
                    disabled={loading}
                  />
                </Tooltip>

                {/* Keyword count bar */}
                <div style={{marginTop:'.6rem', display:'flex', alignItems:'center', gap:'.75rem'}}>
                  <div style={{flex:1, display:'flex', gap:3}}>
                    {Array.from({length: MAX_KEYWORDS}).map((_, i) => (
                      <div
                        key={i}
                        style={{
                          flex: 1, height: 3, borderRadius: 3,
                          background: i < keywords.length ? 'var(--secondary)' : 'var(--surface-3)',
                          transition: 'background .25s',
                        }}
                      />
                    ))}
                  </div>
                  <span style={{fontSize:'.65rem',color:'var(--text-3)',fontFamily:'var(--font-mono)',flexShrink:0}}>
                    {keywords.length} / {MAX_KEYWORDS}
                  </span>
                </div>

                {keywords.length === 0 && (
                  <div className="keyword-suggestions">
                    <span className="keyword-sugg-label">Try examples:</span>
                    {[
                      ['machine learning', 'neural networks', 'image classification'],
                      ['climate change', 'carbon emissions', 'sustainability'],
                      ['drug delivery', 'nanoparticles', 'oncology'],
                    ].map((group, gi) => (
                      <button
                        key={gi}
                        type="button"
                        className="keyword-sugg-btn"
                        onClick={() => setKeywords(group)}
                        disabled={loading}
                      >
                        {group.join(' · ')}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* ── Focus + submit row ── */}
            <div className="search-row" style={{marginTop:'1rem'}}>
              <div className="focus-group">
                <label className="focus-label" style={{ display: 'flex', alignItems: 'center', gap: '.4rem' }}>
                  Focus Filter
                  <InfoTip
                    text="Narrows results to journals that primarily publish in a specific domain. 'General / Best Fit' considers all fields and picks the best match regardless of discipline."
                    placement="top"
                  />
                </label>
                <Tooltip
                  text="Select a domain to prioritise journals in that field. Useful if your paper spans disciplines but you want to target a specific community."
                  placement="top"
                  maxWidth={250}
                  className="w-full"
                >
                  <select
                    className="focus-select"
                    value={focus}
                    onChange={e => setFocus(e.target.value)}
                    disabled={loading}
                  >
                    {FOCUS_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                </Tooltip>
              </div>

              <Tooltip
                text={
                  searchMode === 'keyword'
                    ? 'Runs your keywords through semantic expansion then ranks all 29,553 journals using BM25 + BERT hybrid scoring.'
                    : 'Runs BM25 keyword matching + BERT semantic ranking simultaneously across 29,553 journals, then combines scores for the best results.'
                }
                placement="top"
                maxWidth={280}
              >
                <button
                  className="btn-search"
                  type="submit"
                  disabled={loading || !isSubmittable}
                >
                  {loading
                    ? 'Analyzing…'
                    : searchMode === 'keyword'
                      ? '🔍 Find Journals →'
                      : '🔍 Execute Neural Search →'
                  }
                </button>
              </Tooltip>
            </div>

            {/* ── Result filters ── */}
            <div className="search-filters-row">
              <span className="search-filters-label">
                <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
                  <path d="M1 2h12M3 7h8M5 12h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                </svg>
                Result Filters
                <InfoTip
                  text="Optional pre-filters applied to results. Only journals meeting both thresholds will be shown. Leave blank to see all matches."
                  placement="right"
                />
              </span>

              <Tooltip
                text="H-index reflects a journal's cumulative impact — the number h such that h papers have each been cited at least h times. Higher values indicate a more influential journal. Typical Q1 journals: H-index > 100."
                placement="top"
                maxWidth={290}
              >
                <div className="search-filter-group">
                  <label className="search-filter-label">H-index ≥</label>
                  <input
                    type="number"
                    className="search-filter-input"
                    placeholder="any"
                    min="0"
                    disabled={loading}
                    value={minHIndex === 0 ? '' : minHIndex}
                    onChange={e => setMinHIndex(e.target.value === '' ? 0 : Math.max(0, parseInt(e.target.value) || 0))}
                  />
                </div>
              </Tooltip>

              <Tooltip
                text="SJR (SCImago Journal Rank) weights each citation by the prestige of the journal that cited it — similar to Google PageRank for journals. Values > 1.0 indicate above-average influence."
                placement="top"
                maxWidth={290}
              >
                <div className="search-filter-group">
                  <label className="search-filter-label">SJR ≥</label>
                  <input
                    type="number"
                    className="search-filter-input"
                    placeholder="any"
                    min="0"
                    step="0.1"
                    disabled={loading}
                    value={minSJR === 0 ? '' : minSJR}
                    onChange={e => setMinSJR(e.target.value === '' ? 0 : Math.max(0, parseFloat(e.target.value) || 0))}
                  />
                </div>
              </Tooltip>

              {(minHIndex > 0 || minSJR > 0) && (
                <button
                  type="button"
                  className="search-filter-clear"
                  onClick={() => { setMinHIndex(0); setMinSJR(0); }}
                >
                  ✕ Clear
                </button>
              )}
            </div>

          </div>

          {error && <div className="error-msg" style={{marginTop:'.75rem'}}>{error}</div>}
        </form>

        {loading && (
          <div className="loading-state animate-fade-in">
            <div className="loading-ring" />
            <div className="loading-step">{loadingSteps[loadingStep]}</div>
            <div className="loading-sub">Typically 5–15 seconds on first run</div>
          </div>
        )}

        {/* Stats strip */}
        {!loading && (
          <div className="search-stats-strip animate-fade-up-3">
            {[
              { num: '29,553', label: 'Indexed Journals',  green: false, placement: 'top-start' },
              { num: '3-Tier', label: 'Strategy Plans',    green: false, placement: 'top' },
              { num: 'BERT',   label: 'Semantic Matching', green: true,  placement: 'top' },
              { num: 'Q1–Q4',  label: 'Quartile Coverage', green: false, placement: 'top' },
            ].map(s => (
              <Tooltip key={s.label} text={STAT_TIPS[s.label]} placement={s.placement} maxWidth={240} className="w-full">
                <div className="stat-strip-item">
                  <div className={'stat-strip-num' + (s.green ? ' green' : '')}>{s.num}</div>
                  <div className="stat-strip-label">{s.label}</div>
                </div>
              </Tooltip>
            ))}
          </div>
        )}
      </div>

      {/* ── Right column — neural viz + floating cards ── */}
      <div className="search-right animate-fade-in">
        <div className="neural-canvas">
          <NeuralViz />

          <Tooltip text="BERT (Bidirectional Encoder Representations from Transformers) reads your full abstract and encodes its meaning into a 768-dimensional vector for deep semantic matching." placement="left" maxWidth={260} className="float-card float-card-1">
            <div className="float-card-icon green">🧠</div>
            <div>
              <div className="float-card-label">Semantic Engine</div>
              <div className="float-card-value">BERT Implemented</div>
            </div>
          </Tooltip>

          <Tooltip text="BM25 handles keyword frequency matching while BERT captures deeper meaning. Both scores are normalised and combined into a single hybrid relevance score." placement="right" maxWidth={260} className="float-card float-card-2">
            <div className="float-card-icon indigo">⚡</div>
            <div>
              <div className="float-card-label">Ranking Model</div>
              <div className="float-card-value">BM25 + BERT Hybrid</div>
            </div>
          </Tooltip>
        </div>
      </div>

    </div>
  );
}
