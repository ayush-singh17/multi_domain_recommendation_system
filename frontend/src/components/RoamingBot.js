import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import API from '../api/axios';

// ── Driver.js tour definitions per route ─────────────────────────────────────
const TOURS = {
  '/': [
    {
      popover: {
        title: '👋 Welcome to Journal Finder',
        description: 'This quick tour walks you through every feature. You\'ll learn how to search, interpret results, and build a smart submission strategy in under 2 minutes.',
      },
    },
    {
      element: '#tab-abstract',
      popover: {
        title: '📄 Abstract Mode',
        description: 'Paste your full manuscript abstract (100–250 words). BERT reads the complete semantic meaning of your text — not just individual words — giving you the most accurate journal matches.',
        side: 'bottom', align: 'start',
      },
    },
    {
      element: '#tab-keywords',
      popover: {
        title: '🏷️ Keyword Mode',
        description: 'Prefer keywords over a full abstract? Type up to 10 research topics. The system automatically expands them into a rich semantic sentence before ranking journals — great for early-stage papers.',
        side: 'bottom', align: 'start',
      },
    },
    {
      element: '.abstract-input, .keyword-input-area',
      popover: {
        title: '✍️ Your Research Input',
        description: 'In Abstract mode, aim for 100–250 words — BERT\'s sweet spot. In Keyword mode, press Enter or comma after each term. The word-count bar below tracks your progress in real time.',
        side: 'right', align: 'start',
      },
    },
    {
      element: '.focus-group',
      popover: {
        title: '🎯 Focus Filter',
        description: 'Narrows results to journals that primarily publish in a specific academic domain. Use "General / Best Fit" for interdisciplinary work, or pick a domain like "Clinical Impact" or "Technical / Engineering" to target a specific community.',
        side: 'top', align: 'start',
      },
    },
    {
      element: '.search-filters-row',
      popover: {
        title: '⚙️ Pre-Search Filters',
        description: 'Set minimum thresholds before searching. H-index ≥ 100 narrows to high-impact journals. SJR ≥ 1.0 filters to above-average prestige. Leave blank to see all matches — you can also filter after seeing results.',
        side: 'top', align: 'start',
      },
    },
    {
      element: '.btn-search',
      popover: {
        title: '🔍 Run the Search',
        description: 'Triggers a hybrid BM25 + BERT ranking pass across all 29,553 indexed journals simultaneously. BM25 scores keyword frequency; BERT scores semantic meaning. Both are normalised and combined. Expect results in 5–15 seconds.',
        side: 'top', align: 'end',
      },
    },
    {
      element: '.search-stats-strip',
      popover: {
        title: '📊 System Coverage',
        description: '29,553 peer-reviewed journals from Scopus, DOAJ, and SciMago. Results come back as one ranked list that you can filter, sort and page through. Hover any stat card to see the full explanation.',
        side: 'top', align: 'start',
      },
    },
    {
      element: '.float-card-1, .float-card-2',
      popover: {
        title: '🧠 The Neural Engine',
        description: 'BERT encodes your abstract into a 768-dimensional semantic vector. BM25 runs keyword frequency scoring in parallel. These two signals are merged into one hybrid relevance score for every journal in the database.',
        side: 'left', align: 'start',
      },
    },
    {
      element: '.float-card-3',
      popover: {
        title: '🏛️ MAHE Approved Journals',
        description: 'Results are cross-referenced against the official MAHE (Manipal Academy of Higher Education) Approved Journals list. On the results page, you can filter by "MAHE Approved" to see only approved journals — each marked with a teal "MAHE ✓" badge.',
        side: 'left', align: 'start',
      },
    },
  ],

  '/results': [
    {
      popover: {
        title: '📋 Your Results Are Ready',
        description: 'A quick tour of this page: the ranked list, filters and sorting, journal details, the timeline planner, comparing journals and your PDF report.',
      },
    },
    {
      element: '.rv2-summary',
      popover: {
        title: '📊 Search Summary',
        description: 'How many journals matched your abstract, how many of the ones shown are Q1 or low risk, and the focus mode you used. High-risk journals are hidden automatically.',
        side: 'bottom', align: 'start',
      },
    },
    {
      element: '.rv2-sidebar, .rv2-filters-btn',
      popover: {
        title: '🧰 Filters',
        description: 'Tick several quartiles (Q1–Q4) or risk levels at once, show only MAHE-approved or open-access journals, or type a word to search inside the results. The numbers show how many journals each option would give you.',
        side: 'right', align: 'start',
      },
    },
    {
      element: '.rv2-fieldset--note',
      desktopOnly: true,
      popover: {
        title: '🎚️ Q3 / Q4 Limit',
        description: 'By default the list keeps at most 2 Q3 and 2 Q4 journals so stronger options stay on top. Untick this to see every match in every quartile.',
        side: 'right', align: 'start',
      },
    },
    {
      element: '.rv2-toolbar',
      popover: {
        title: '↕️ Sort & Page Size',
        description: 'Results start in best-match order. Sort by SJR, H-index or title instead, and choose 10, 20 or 30 journals per page. Filters apply to the whole list before it is split into pages.',
        side: 'bottom', align: 'start',
      },
    },
    {
      element: '.rv2-row',
      popover: {
        title: '📖 A Result Row',
        description: 'Each row shows the rank, journal and publisher, badges for quartile, risk, MAHE approval and open access, plus the match score, SJR and H-index. The coloured stripe on the left follows the quartile.',
        side: 'bottom', align: 'start',
      },
    },
    {
      element: '.rv2-actions',
      popover: {
        title: '⚡ Row Actions',
        description: '“+ Timeline” adds the journal to your submission plan, “Compare” selects it for a side-by-side comparison (up to 3), and “Details” opens the full journal card.',
        side: 'left', align: 'start',
      },
    },
    {
      element: '.rv2-details',
      needsDetails: true,
      popover: {
        title: '🗂️ Journal Details',
        description: 'The full card: SJR, H-index, estimated time to review, APC and open-access status, ISSN, categories, a 5-year citation trend and a link to the journal website.',
        side: 'top', align: 'start',
      },
    },
    {
      element: '.why-accordion',
      needsDetails: true,
      popover: {
        title: '💡 Why Recommended',
        description: 'Expand this to see which terms from your abstract matched, a plain-language explanation of the relevance, and risk signals (✓ good, ~ caution, ■ warning).',
        side: 'top', align: 'start',
      },
    },
    {
      element: '.rv2-pager',
      popover: {
        title: '📄 Pagination',
        description: 'Move through the full ranked list page by page. Pages reset whenever you change a filter or the sort order.',
        side: 'top', align: 'center',
      },
    },
    {
      element: '.rv2-tabs',
      popover: {
        title: '🗓️ Results & Timeline Planner',
        description: 'Switch between the ranked list and the Timeline planner. Journals you add with “+ Timeline” stay in the planner while you filter or page through results.',
        side: 'bottom', align: 'start',
      },
    },
    {
      element: '.rv2-tl-controls',
      view: 'timeline',
      popover: {
        title: '🧭 Timeline Planner',
        description: 'Add journals here or from the results, put them in the order you would try them, and edit the assumed decision time for each. A chart shows when each submission starts and when a decision is expected. These are planning assumptions, not predictions.',
        side: 'bottom', align: 'start',
      },
    },
    {
      element: '.rv2-summary-actions',
      popover: {
        title: '📥 Download PDF Report',
        description: 'Generates a formatted, shareable PDF with your top-ranked journals, match scores and risk details. Handy for sharing with co-authors or advisors. It can take 5–10 seconds.',
        side: 'bottom', align: 'end',
      },
    },
    {
      element: '.rv2-compare',
      popover: {
        title: '⇄ Compare Journals',
        description: 'Tick “Compare” on up to 3 journals. A bar appears at the bottom — press “Compare now” for a side-by-side breakdown of their metrics.',
        side: 'left', align: 'start',
      },
    },
  ],
};

// ── Helpers for the results-page demo (it opens panels and switches tabs as it goes) ──
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const isVisible = el => {
  if (!el) return false;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0 && r.right > 0 && r.left < window.innerWidth;
};
// First selector (comma + space separated) whose element is on screen; else the first that exists.
const pickElement = selectors => {
  const list = selectors.split(', ').map(sel => document.querySelector(sel));
  return list.find(isVisible) || list.find(Boolean) || null;
};
const clickTab = name => {
  const tab = [...document.querySelectorAll('.rv2-tabs [role="tab"]')]
    .find(b => b.textContent.trim().toLowerCase().startsWith(name));
  if (tab && tab.getAttribute('aria-selected') !== 'true') tab.click();
};

const HELP_CONTENT = [
  { icon: '📄', title: 'Abstract Mode',      desc: 'Paste 100–250 words. BERT reads full semantic meaning for the most accurate matches.' },
  { icon: '🏷️', title: 'Keyword Mode',       desc: 'Add up to 10 topics. They\'re expanded into semantic context automatically before ranking.' },
  { icon: '📋', title: 'Ranked Results',     desc: 'Browse the full recommendation list best match first, with 10, 20 or 30 journals per page and a sort menu.' },
  { icon: '🔖', title: 'Filters',            desc: 'Use the filter panel to pick quartiles (Q1 = top 25% impact), risk level, MAHE approval or open access, or to search within results.' },
  { icon: '💡', title: 'Why Recommended',    desc: 'Press Details on a result, then expand “Why Recommended” to see matched terms, relevance reasoning and the score breakdown.' },
  { icon: '📥', title: 'PDF Report',         desc: 'Download a formatted PDF of your top-ranked journals to share with co-authors or advisors.' },
  { icon: '🗓️', title: 'Timeline Planner',   desc: 'Press “+ Timeline” on any result, order your sequence, and edit the assumed decision and revision times.' },
  { icon: '📁', title: 'History Tab',        desc: 'Every search is saved. Revisit past results anytime from the History tab in the navbar.' },
];

// Roaming anchor points: far right edge only — menu always opens leftward
const ROAM_ANCHORS = [
  { x: 94, y: 12  },   // top-right
  { x: 95, y: 25  },   // upper-right
  { x: 94, y: 78  },   // bottom-right
  { x: 95, y: 65  },   // lower-right
  { x: 93, y: 46  },   // mid-right
];

// ── Feedback type options ─────────────────────────────────────────────────────
const FEEDBACK_TYPES = [
  { key: 'bug',     label: 'Bug Report',       icon: '🐛' },
  { key: 'feature', label: 'Feature Request',   icon: '✨' },
  { key: 'general', label: 'General Feedback',  icon: '💬' },
];

// ── RoamingBot component ──────────────────────────────────────────────────────
export default function RoamingBot() {
  const location = useLocation();

  const [anchorIdx, setAnchorIdx] = useState(0);
  const [menu, setMenu]           = useState(false);
  const [help, setHelp]           = useState(false);
  const [feedback, setFeedback]   = useState(false);
  const [bubble, setBubble]       = useState(false);
  const [moving, setMoving]       = useState(false);
  const [blinking, setBlinking]   = useState(false);

  // Feedback form state
  const [fbType, setFbType]       = useState('general');
  const [fbRating, setFbRating]   = useState(0);
  const [fbHover, setFbHover]     = useState(0);
  const [fbMessage, setFbMessage] = useState('');
  const [fbSending, setFbSending] = useState(false);
  const [fbSent, setFbSent]       = useState(false);

  const roamTimer   = useRef(null);
  const bubbleTimer = useRef(null);
  const blinkTimer  = useRef(null);
  const menuRef     = useRef(null);
  const botRef      = useRef(null);

  const pos = ROAM_ANCHORS[anchorIdx];

  // ── Roaming logic — cycles through right-side anchors ──
  const roam = useCallback(() => {
    if (menu || help || feedback) return;
    setAnchorIdx(prev => {
      let next;
      do { next = Math.floor(Math.random() * ROAM_ANCHORS.length); }
      while (next === prev);
      return next;
    });
    setMoving(true);
    setTimeout(() => setMoving(false), 1400);
  }, [menu, help, feedback]);

  // ── Speech bubble ──
  const showBubble = useCallback(() => {
    if (menu || help || feedback) return;
    setBubble(true);
    setTimeout(() => setBubble(false), 3500);
  }, [menu, help, feedback]);

  // ── Blink ──
  useEffect(() => {
    const blink = () => {
      setBlinking(true);
      setTimeout(() => setBlinking(false), 160);
    };
    blinkTimer.current = setInterval(blink, 3000 + Math.random() * 2000);
    return () => clearInterval(blinkTimer.current);
  }, []);

  // ── Start roam + bubble timers ──
  useEffect(() => {
    // Longer interval = leisurely, organic wandering
    roamTimer.current   = setInterval(roam, 10000 + Math.random() * 6000);
    bubbleTimer.current = setInterval(showBubble, 18000);
    const first = setTimeout(showBubble, 5000);
    return () => {
      clearInterval(roamTimer.current);
      clearInterval(bubbleTimer.current);
      clearTimeout(first);
    };
  }, [roam, showBubble]);

  // ── Click outside closes menu ──
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target) &&
          botRef.current  && !botRef.current.contains(e.target)) {
        setMenu(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // ── Adaptive menu alignment — pick anchor direction based on owl's viewport position ──
  const menuAlign = useMemo(() => {
    if (pos.y < 30) return 'roam-menu--align-top';       // owl near top → menu hangs below
    if (pos.y > 60) return 'roam-menu--align-bottom';    // owl near bottom → menu rises above
    return 'roam-menu--align-center';                    // owl in middle → centred
  }, [pos.y]);

  // ── Driver.js tour ──
  const startDemo = useCallback(async () => {
    setMenu(false);
    const spec = TOURS[location.pathname] || TOURS['/'];
    const onResults = location.pathname === '/results';
    const opened = { details: false };

    // Results page: some steps need a panel opened or another tab shown first.
    const prepare = async step => {
      if (!onResults || !step) return;
      clickTab(step.view === 'timeline' ? 'timeline' : 'results');
      if (step.needsDetails && !document.querySelector('.rv2-details')) {
        const toggle = document.querySelector('.rv2-row .rv2-btn--ghost[aria-expanded="false"]');
        if (toggle) { toggle.click(); opened.details = true; }
      }
      await wait(350);
    };
    const restore = () => {
      if (!onResults) return;
      clickTab('results');
      if (opened.details) document.querySelector('.rv2-row .rv2-btn--ghost[aria-expanded="true"]')?.click();
    };

    const steps = spec
      .filter(s => {
        if (!s.element) return true;                                   // intro slides
        if (onResults && (s.needsDetails || s.view === 'timeline')) return true;   // appear after we prepare them
        const el = pickElement(s.element);
        return s.desktopOnly ? isVisible(el) : Boolean(el);
      })
      .map(s => !s.element ? s
        : onResults ? { ...s, element: () => pickElement(s.element) }
        : { ...s, element: s.element.split(', ').find(sel => document.querySelector(sel)) });

    let driverObj;
    const stepsWithHooks = onResults ? steps.map((s, i) => ({
      ...s,
      popover: {
        ...s.popover,
        onNextClick: async () => { await prepare(steps[i + 1]); driverObj.moveNext(); },
        onPrevClick: async () => { await prepare(steps[i - 1]); driverObj.movePrevious(); },
      },
    })) : steps;

    driverObj = driver({
      showProgress: true,
      animate: true,
      smoothScroll: true,
      overlayOpacity: 0.55,
      popoverClass: 'bot-driver-popover',
      nextBtnText: 'Next →',
      prevBtnText: '← Back',
      doneBtnText: 'Got it! 🎉',
      onDestroyStarted: () => { restore(); driverObj.destroy(); },
      steps: stepsWithHooks,
    });
    driverObj.drive();
  }, [location.pathname]);

  const handleBotClick = () => {
    setBubble(false);
    setMenu(m => !m);
  };

  // ── Open feedback modal ──
  const openFeedback = () => {
    setMenu(false);
    setFbType('general');
    setFbRating(0);
    setFbHover(0);
    setFbMessage('');
    setFbSent(false);
    setFeedback(true);
  };

  // ── Submit feedback ──
  const submitFeedback = async () => {
    if (!fbMessage.trim()) return;
    setFbSending(true);
    try {
      await API.post('/search/feedback/', {
        feedback_type: fbType,
        rating: fbRating || null,
        message: fbMessage.trim(),
      });
      setFbSent(true);
      setTimeout(() => {
        setFeedback(false);
        setFbSent(false);
      }, 2000);
    } catch (err) {
      console.error('Feedback submission failed:', err);
    } finally {
      setFbSending(false);
    }
  };

  return (
    <>
      {/* ── Scholar bot + menu ── */}
      <div
        className={`roam-bot-wrap ${moving ? 'roam-moving' : ''}`}
        style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
      >
        {/* Speech bubble */}
        {bubble && !menu && (
          <div className="roam-bubble">Ask your scholar! 🎓</div>
        )}

        {/* The scholar bot */}
        <button
          ref={botRef}
          className={`roam-bot ${menu ? 'roam-bot--active' : ''}`}
          onClick={handleBotClick}
          aria-label="Scholar helper"
        >
          <ScholarSVG blinking={blinking} moving={moving} />
        </button>

        {/* ── Redesigned Menu — card-style with owl avatar ── */}
        {menu && (
          <div ref={menuRef} className={`roam-menu ${menuAlign}`}>
            {/* Owl avatar header */}
            <div className="roam-menu-avatar-section">
              <div className="roam-menu-avatar-ring">
                <ScholarSVG blinking={false} moving={false} size={48} />
              </div>
              <div className="roam-menu-greeting">
                <div className="roam-menu-greeting-title">How can I help?</div>
                <div className="roam-menu-greeting-sub">Your research assistant is ready</div>
              </div>
            </div>

            <div className="roam-menu-divider" />

            {/* Option 1: Interactive Demo */}
            <button className="roam-menu-btn" onClick={startDemo}>
              <span className="roam-menu-btn-icon-wrap">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.8"/>
                  <path d="M10 8.5V15.5L16 12L10 8.5Z" fill="currentColor"/>
                </svg>
              </span>
              <div>
                <div className="roam-menu-btn-title">Take Interactive Demo</div>
                <div className="roam-menu-btn-sub">Explore all features step-by-step</div>
              </div>
            </button>

            {/* Option 2: Quick Help */}
            <button className="roam-menu-btn" onClick={() => { setMenu(false); setHelp(true); }}>
              <span className="roam-menu-btn-icon-wrap">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M4 4H14L20 10V20C20 20.5523 19.5523 21 19 21H5C4.44772 21 4 20.5523 4 20V4Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
                  <path d="M14 4V10H20" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
                  <line x1="8" y1="14" x2="16" y2="14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  <line x1="8" y1="17" x2="13" y2="17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </span>
              <div>
                <div className="roam-menu-btn-title">Quick Help Guide</div>
                <div className="roam-menu-btn-sub">Tips & feature reference</div>
              </div>
            </button>

            {/* Option 3: Submit Feedback */}
            <button className="roam-menu-btn" onClick={openFeedback}>
              <span className="roam-menu-btn-icon-wrap">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M16.474 5.408l2.118 2.118m-.756-3.982L12.109 9.27a2.118 2.118 0 00-.58 1.082L11 13l2.648-.53a2.118 2.118 0 001.082-.58l5.727-5.727a1.853 1.853 0 10-2.621-2.621z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M19 15v3a2 2 0 01-2 2H6a2 2 0 01-2-2V7a2 2 0 012-2h3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </span>
              <div>
                <div className="roam-menu-btn-title">Submit Feedback</div>
                <div className="roam-menu-btn-sub">Report a bug or suggest an improvement</div>
              </div>
            </button>
          </div>
        )}
      </div>

      {/* ── Help panel ── */}
      {help && (
        <div className="roam-help-backdrop" onClick={() => setHelp(false)}>
          <div className="roam-help-panel" onClick={e => e.stopPropagation()}>
            <div className="roam-help-header">
              <div className="roam-help-title">
                <ScholarSVG blinking={false} moving={false} size={32} />
                <span>Quick Reference</span>
              </div>
              <button className="roam-help-close" onClick={() => setHelp(false)}>✕</button>
            </div>
            <div className="roam-help-grid">
              {HELP_CONTENT.map((item, i) => (
                <div key={i} className="roam-help-item">
                  <div className="roam-help-item-icon">{item.icon}</div>
                  <div>
                    <div className="roam-help-item-title">{item.title}</div>
                    <div className="roam-help-item-desc">{item.desc}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="roam-help-footer">
              <button className="roam-help-demo-btn" onClick={() => { setHelp(false); startDemo(); }}>
                🎬 Launch Guided Demo
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Feedback Modal ── */}
      {feedback && (
        <div className="roam-help-backdrop" onClick={() => setFeedback(false)}>
          <div className="roam-feedback-panel" onClick={e => e.stopPropagation()}>
            {/* Success state */}
            {fbSent ? (
              <div className="roam-feedback-success">
                <div className="roam-feedback-success-icon">✓</div>
                <div className="roam-feedback-success-title">Thank you!</div>
                <div className="roam-feedback-success-sub">Your feedback has been submitted successfully.</div>
              </div>
            ) : (
              <>
                {/* Header */}
                <div className="roam-feedback-header">
                  <div className="roam-feedback-header-left">
                    <div className="roam-feedback-avatar-ring">
                      <ScholarSVG blinking={false} moving={false} size={36} />
                    </div>
                    <div>
                      <div className="roam-feedback-title">Submit Feedback</div>
                      <div className="roam-feedback-subtitle">Help us improve Journal Finder</div>
                    </div>
                  </div>
                  <button className="roam-help-close" onClick={() => setFeedback(false)}>✕</button>
                </div>

                <div className="roam-feedback-body">
                  {/* Feedback type chips */}
                  <div className="roam-feedback-label">Feedback Type</div>
                  <div className="roam-feedback-chips">
                    {FEEDBACK_TYPES.map(t => (
                      <button
                        key={t.key}
                        className={`roam-feedback-chip ${fbType === t.key ? 'roam-feedback-chip--active' : ''}`}
                        onClick={() => setFbType(t.key)}
                      >
                        <span>{t.icon}</span>
                        <span>{t.label}</span>
                      </button>
                    ))}
                  </div>

                  {/* Star rating */}
                  <div className="roam-feedback-label">Rating <span className="roam-feedback-optional">(optional)</span></div>
                  <div className="roam-feedback-stars">
                    {[1, 2, 3, 4, 5].map(star => (
                      <button
                        key={star}
                        className={`roam-feedback-star ${star <= (fbHover || fbRating) ? 'roam-feedback-star--filled' : ''}`}
                        onClick={() => setFbRating(star === fbRating ? 0 : star)}
                        onMouseEnter={() => setFbHover(star)}
                        onMouseLeave={() => setFbHover(0)}
                        aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
                      >
                        <svg width="22" height="22" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
                            fill={star <= (fbHover || fbRating) ? 'currentColor' : 'none'}
                            stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                        </svg>
                      </button>
                    ))}
                  </div>

                  {/* Message textarea */}
                  <div className="roam-feedback-label">Your Message</div>
                  <textarea
                    className="roam-feedback-textarea"
                    placeholder="Tell us what you think… describe a bug, request a feature, or share any thoughts."
                    value={fbMessage}
                    onChange={e => setFbMessage(e.target.value)}
                    rows={4}
                  />

                  {/* Submit */}
                  <button
                    className="roam-feedback-submit"
                    onClick={submitFeedback}
                    disabled={!fbMessage.trim() || fbSending}
                  >
                    {fbSending ? (
                      <span className="roam-feedback-spinner" />
                    ) : (
                      <>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{marginRight: 6}}>
                          <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                        Send Feedback
                      </>
                    )}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

// ── Scholar Owl SVG ───────────────────────────────────────────────────────────
// An academic owl with graduation cap — universal symbol of wisdom & scholarship
function ScholarSVG({ blinking, moving, size = 56 }) {
  return (
    <svg
      width={size} height={size}
      viewBox="0 0 56 56"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`roam-bot-svg ${moving ? 'roam-bot-svg--walk' : ''}`}
    >
      <defs>
        <radialGradient id="owlBody" cx="50%" cy="40%" r="55%">
          <stop offset="0%"   stopColor="#6B7FD7"/>
          <stop offset="100%" stopColor="#3A4AB8"/>
        </radialGradient>
        <radialGradient id="owlFace" cx="50%" cy="45%" r="50%">
          <stop offset="0%"   stopColor="#F5EDD8"/>
          <stop offset="100%" stopColor="#E8D9BC"/>
        </radialGradient>
        <radialGradient id="eyeL" cx="40%" cy="35%" r="60%">
          <stop offset="0%"   stopColor="#fff"/>
          <stop offset="100%" stopColor="#EEF2FF"/>
        </radialGradient>
        <radialGradient id="eyeR" cx="40%" cy="35%" r="60%">
          <stop offset="0%"   stopColor="#fff"/>
          <stop offset="100%" stopColor="#EEF2FF"/>
        </radialGradient>
        <linearGradient id="capTop" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stopColor="#1E1B4B"/>
          <stop offset="100%" stopColor="#312E81"/>
        </linearGradient>
        <linearGradient id="capBrim" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor="#2D2A6E"/>
          <stop offset="100%" stopColor="#3730A3"/>
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="1.2" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      {/* ── Body / wings ── */}
      {/* Left wing */}
      <ellipse cx="14" cy="36" rx="9" ry="13" fill="#4A5BC4" opacity="0.9"
        className={moving ? 'roam-arm-l' : ''}
        style={{ transformOrigin: '18px 28px' }}
      />
      {/* Right wing */}
      <ellipse cx="42" cy="36" rx="9" ry="13" fill="#4A5BC4" opacity="0.9"
        className={moving ? 'roam-arm-r' : ''}
        style={{ transformOrigin: '38px 28px' }}
      />
      {/* Main body */}
      <ellipse cx="28" cy="36" rx="14" ry="16" fill="url(#owlBody)"/>

      {/* Belly / chest patch */}
      <ellipse cx="28" cy="39" rx="8" ry="10" fill="rgba(255,255,255,0.13)"/>

      {/* ── Head ── */}
      <circle cx="28" cy="22" r="14" fill="url(#owlBody)"/>

      {/* Ear tufts */}
      <path d="M18 11 Q16 5 21 8 Z" fill="#3A4AB8"/>
      <path d="M38 11 Q40 5 35 8 Z" fill="#3A4AB8"/>

      {/* ── Face disc ── */}
      <ellipse cx="28" cy="24" rx="10" ry="9" fill="url(#owlFace)"/>

      {/* ── Eyes ── */}
      {/* Left eye socket */}
      <circle cx="22" cy="23" r="5.5" fill="url(#eyeL)" stroke="rgba(60,70,180,0.2)" strokeWidth="0.8"/>
      {/* Right eye socket */}
      <circle cx="34" cy="23" r="5.5" fill="url(#eyeR)" stroke="rgba(60,70,180,0.2)" strokeWidth="0.8"/>

      {/* Pupils — blink by shrinking */}
      {blinking ? (
        <>
          <ellipse cx="22" cy="23" rx="3.5" ry="0.8" fill="#1E1B4B"/>
          <ellipse cx="34" cy="23" rx="3.5" ry="0.8" fill="#1E1B4B"/>
        </>
      ) : (
        <>
          <circle cx="22" cy="23" r="3.5" fill="#1E1B4B"/>
          <circle cx="34" cy="23" r="3.5" fill="#1E1B4B"/>
          {/* Iris highlight */}
          <circle cx="22" cy="23" r="1.8" fill="#5B6FE8"/>
          <circle cx="34" cy="23" r="1.8" fill="#5B6FE8"/>
          {/* Catchlight */}
          <circle cx="23.4" cy="21.6" r="1" fill="white" opacity="0.9"/>
          <circle cx="35.4" cy="21.6" r="1" fill="white" opacity="0.9"/>
        </>
      )}

      {/* Beak */}
      <path d="M25.5 27.5 L28 31 L30.5 27.5 Z" fill="#D4A057"/>
      <line x1="25.5" y1="27.5" x2="30.5" y2="27.5" stroke="#B8883C" strokeWidth="0.5"/>

      {/* ── Graduation cap ── */}
      {/* Cap brim */}
      <rect x="13" y="10" width="30" height="3.5" rx="1" fill="url(#capBrim)"/>
      {/* Cap top */}
      <path d="M18 10 L28 3 L38 10 Z" fill="url(#capTop)"/>
      {/* Tassel string */}
      <line x1="38" y1="10" x2="42" y2="16" stroke="#F59E0B" strokeWidth="1.2" strokeLinecap="round"/>
      {/* Tassel end */}
      <circle cx="42" cy="16" r="2" fill="#F59E0B" filter="url(#glow)">
        <animateTransform attributeName="transform" type="rotate"
          values="0 42 14;12 42 14;-8 42 14;0 42 14"
          dur="2.5s" repeatCount="indefinite" calcMode="spline"
          keySplines="0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1"/>
      </circle>

      {/* ── Feet / perch ── */}
      <path d="M22 51 L20 55 M22 51 L22 55 M22 51 L24 55" stroke="#D4A057" strokeWidth="1.4" strokeLinecap="round"/>
      <path d="M34 51 L32 55 M34 51 L34 55 M34 51 L36 55" stroke="#D4A057" strokeWidth="1.4" strokeLinecap="round"/>
      <ellipse cx="22" cy="51" rx="4" ry="2" fill="#4A5BC4" opacity="0.8"/>
      <ellipse cx="34" cy="51" rx="4" ry="2" fill="#4A5BC4" opacity="0.8"/>

      {/* ── Knowledge sparkle (idle only) ── */}
      {!moving && (
        <g filter="url(#glow)">
          <circle cx="8" cy="20" r="1.2" fill="#F59E0B" opacity="0.8">
            <animate attributeName="opacity" values="0.8;0.1;0.8" dur="2.1s" repeatCount="indefinite"/>
            <animate attributeName="r" values="1.2;1.8;1.2" dur="2.1s" repeatCount="indefinite"/>
          </circle>
          <circle cx="48" cy="18" r="1" fill="#A78BFA" opacity="0.7">
            <animate attributeName="opacity" values="0.7;0.1;0.7" dur="1.7s" repeatCount="indefinite"/>
            <animate attributeName="r" values="1;1.6;1" dur="1.7s" repeatCount="indefinite"/>
          </circle>
          <circle cx="50" cy="30" r="0.8" fill="#34D399" opacity="0.6">
            <animate attributeName="opacity" values="0.6;0.1;0.6" dur="2.4s" repeatCount="indefinite"/>
          </circle>
        </g>
      )}
    </svg>
  );
}
