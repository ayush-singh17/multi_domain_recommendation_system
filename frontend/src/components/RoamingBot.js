import { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';

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
        description: '29,553 peer-reviewed journals from Scopus, DOAJ, and SciMago. Results are always split into 3 strategy tiers (Plan A / B / C). Hover any stat card to see the full explanation.',
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
  ],

  '/results': [
    {
      popover: {
        title: '📋 Your Results Are Ready',
        description: 'Here\'s a tour of everything on this page — from filtering and tag chips to reading journal cards, understanding recommendations, downloading your PDF report, and comparing journals side by side.',
      },
    },
    {
      element: '.tag-filter-bar',
      popover: {
        title: '🏷️ Quartile & Risk Tags',
        description: 'Click any tag to instantly filter results. Q1–Q4 tags filter by SciMago quartile ranking — Q1 is the top 25% by citation impact. "Low Risk" / "Medium Risk" filter by predatory journal safety score. The number on each tag shows how many journals match. Click again to clear.',
        side: 'bottom', align: 'start',
      },
    },
    {
      element: '.tag-filter-chip.tag-q1, .tag-filter-chip',
      popover: {
        title: '📌 What Do Quartiles Mean?',
        description: 'Q1 = Top 25% journals by citation impact in their field (most competitive, highest visibility). Q2 = 25–50% (balanced impact & acceptance). Q3 = 50–75% (broader scope). Q4 = Bottom 25% (fastest acceptance, least prestige). Always target a spread across Plans A, B, and C.',
        side: 'bottom', align: 'start',
      },
    },
    {
      element: '.plan-section',
      popover: {
        title: '📁 3-Tier Strategy Plans',
        description: 'Plan A = Ambitious Q1 targets — highest impact, most competitive. Plan B = Balanced Q2 journals — strong acceptance odds with solid reputation. Plan C = Safety net — high-acceptance indexed journals for a guaranteed publication. Submit to A first, move to B or C only after rejection.',
        side: 'top', align: 'start',
      },
    },
    {
      element: '.jc-card',
      popover: {
        title: '📖 Journal Card',
        description: 'Each card shows: Match % (semantic relevance score), Quartile, Risk level, Impact Factor, CiteScore, SJR, H-index, estimated Time to Review, Open Access status, and APC cost. All data is sourced from Scopus, DOAJ, and SciMago.',
        side: 'top', align: 'start',
      },
    },
    {
      element: '.why-accordion',
      popover: {
        title: '💡 Why Recommended',
        description: 'Click "Why Recommended" on any journal card to expand the reasoning panel. It shows: matched semantic tokens from your abstract, a plain-language relevance explanation, risk signals (✓ green = good, ~ amber = caution, ✗ red = warning), and the exact BM25 + BERT score breakdown used to rank this journal.',
        side: 'top', align: 'start',
      },
    },
    {
      element: '.timeline-card, .submission-timeline',
      popover: {
        title: '🗓️ Submission Roadmap',
        description: 'A dynamic timeline that re-renders every time you apply a filter tag. It shows optimal submission windows for each plan, parallel-track strategy (submit to A and B simultaneously), and estimated response dates based on the average time-to-review of your filtered journals.',
        side: 'top', align: 'start',
      },
    },
    {
      element: '.results-actions',
      popover: {
        title: '📥 Download PDF Report',
        description: 'The "Download PDF Report" button generates a formatted, shareable PDF of all your results — including journal details, match scores, and your 3-tier strategy. Great for sharing with co-authors or advisors. PDF generation takes 5–10 seconds.',
        side: 'top', align: 'end',
      },
    },
    {
      element: '.btn-compare, .btn-compare-active',
      popover: {
        title: '⇄ Compare Journals',
        description: 'Click "Compare" on up to 3 journal cards to add them to the comparison bar at the bottom. Then click "Compare Selected" to see a side-by-side breakdown of all their metrics — ideal for choosing between similarly ranked journals.',
        side: 'top', align: 'start',
      },
    },
  ],
};

const HELP_CONTENT = [
  { icon: '📄', title: 'Abstract Mode',      desc: 'Paste 100–250 words. BERT reads full semantic meaning for the most accurate matches.' },
  { icon: '🏷️', title: 'Keyword Mode',       desc: 'Add up to 10 topics. They\'re expanded into semantic context automatically before ranking.' },
  { icon: '📁', title: 'Strategy Tiers',     desc: 'Plan A = Q1 ambition, Plan B = balanced Q2, Plan C = safe high-acceptance fallback.' },
  { icon: '🔖', title: 'Q1–Q4 Tag Filters',  desc: 'Filter results by SciMago quartile. Q1 = top 25% impact. Click a tag chip on the results page.' },
  { icon: '💡', title: 'Why Recommended',    desc: 'Expand the accordion on any journal card to see matched tokens, relevance reasoning, and score breakdown.' },
  { icon: '📥', title: 'PDF Report',         desc: 'Download a formatted PDF of your full 3-tier strategy to share with co-authors or advisors.' },
  { icon: '🗓️', title: 'Submission Roadmap', desc: 'A live timeline that updates with every filter. Shows when to submit to each plan.' },
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

// ── RoamingBot component ──────────────────────────────────────────────────────
export default function RoamingBot() {
  const location = useLocation();

  const [anchorIdx, setAnchorIdx] = useState(0);
  const [menu, setMenu]           = useState(false);
  const [help, setHelp]           = useState(false);
  const [bubble, setBubble]       = useState(false);
  const [moving, setMoving]       = useState(false);
  const [blinking, setBlinking]   = useState(false);

  const roamTimer   = useRef(null);
  const bubbleTimer = useRef(null);
  const blinkTimer  = useRef(null);
  const menuRef     = useRef(null);
  const botRef      = useRef(null);

  const pos = ROAM_ANCHORS[anchorIdx];

  // ── Roaming logic — cycles through right-side anchors ──
  const roam = useCallback(() => {
    if (menu || help) return;
    setAnchorIdx(prev => {
      let next;
      do { next = Math.floor(Math.random() * ROAM_ANCHORS.length); }
      while (next === prev);
      return next;
    });
    setMoving(true);
    setTimeout(() => setMoving(false), 1400);
  }, [menu, help]);

  // ── Speech bubble ──
  const showBubble = useCallback(() => {
    if (menu || help) return;
    setBubble(true);
    setTimeout(() => setBubble(false), 3500);
  }, [menu, help]);

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

  // ── Driver.js tour ──
  const startDemo = useCallback(() => {
    setMenu(false);
    const steps = TOURS[location.pathname] || TOURS['/'];
    const validSteps = steps
      .filter(s => {
        // Steps with no element (intro popovers) are always included
        if (!s.element) return true;
        // Steps with an element are only included if at least one selector exists in the DOM
        return s.element.split(', ').some(sel => document.querySelector(sel));
      })
      .map(s => {
        // No element → pass through untouched (Driver.js centres these as intro slides)
        if (!s.element) return s;
        // Pick the first selector that actually exists in the DOM
        const el = s.element.split(', ').find(sel => document.querySelector(sel));
        return { ...s, element: el };
      });

    const driverObj = driver({
      showProgress: true,
      animate: true,
      smoothScroll: true,
      overlayOpacity: 0.55,
      popoverClass: 'bot-driver-popover',
      nextBtnText: 'Next →',
      prevBtnText: '← Back',
      doneBtnText: 'Got it! 🎉',
      onDestroyStarted: () => { driverObj.destroy(); },
      steps: validSteps,
    });
    driverObj.drive();
  }, [location.pathname]);

  const handleBotClick = () => {
    setBubble(false);
    setMenu(m => !m);
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

        {/* Menu — always opens to the LEFT of the mascot */}
        {menu && (
          <div ref={menuRef} className="roam-menu">
            <div className="roam-menu-header">How can I help? 🎓</div>
            <button className="roam-menu-btn" onClick={startDemo}>
              <span className="roam-menu-btn-icon">🎬</span>
              <div>
                <div className="roam-menu-btn-title">Take a Demo</div>
                <div className="roam-menu-btn-sub">Guided tour of the app</div>
              </div>
            </button>
            <button className="roam-menu-btn" onClick={() => { setMenu(false); setHelp(true); }}>
              <span className="roam-menu-btn-icon">📖</span>
              <div>
                <div className="roam-menu-btn-title">Quick Help</div>
                <div className="roam-menu-btn-sub">Tips & feature reference</div>
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
