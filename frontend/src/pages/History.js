import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import API from '../api/axios';

// ── Parse keywords stored as JSON string ──────────────────────────────────────
function parseKeywords(raw) {
  if (!raw) return [];
  try { return JSON.parse(raw); } catch { return []; }
}

// ── Derive topic tags from abstract text ──────────────────────────────────────
function extractTags(abstract, focus) {
  const tags = [];
  if (focus && focus !== 'General / Best Fit') {
    tags.push(focus.split('/')[0].trim().toUpperCase());
  }
  const keywords = {
    'NEURAL NETWORKS':   ['neural', 'deep learning', 'transformer', 'attention mechanism'],
    'MACHINE LEARNING':  ['machine learning', 'reinforcement', 'supervised', 'unsupervised'],
    'NLP':               ['language model', 'nlp', 'text classification', 'bert', 'gpt', 'llm'],
    'BIO-TECH':          ['crispr', 'genomic', 'gene editing', 'dna', 'rna', 'protein', 'molecular'],
    'ETHICS':            ['ethical', 'ethics', 'moral', 'bias', 'fairness', 'policy implications'],
    'QUANTUM COMPUTING': ['quantum', 'qubit', 'entanglement', 'superposition'],
    'CLIMATE':           ['climate', 'carbon', 'emission', 'sustainability', 'environment'],
    'MEDICAL':           ['clinical', 'patient', 'disease', 'treatment', 'drug', 'therapy'],
    'EDGE AI':           ['edge computing', 'embedded', 'iot', 'mobile deployment', 'latency'],
    'ASTRO-PHYSICS':     ['satellite', 'orbit', 'space', 'astronomical', 'telescope'],
    'CYBERSECURITY':     ['security', 'encryption', 'privacy', 'adversarial', 'attack'],
    'SOCIAL SCIENCE':    ['social', 'society', 'community', 'human behavior', 'cultural'],
  };
  const lower = abstract.toLowerCase();
  for (const [tag, words] of Object.entries(keywords)) {
    if (words.some(w => lower.includes(w))) {
      tags.push(tag);
      if (tags.length >= 3) break;
    }
  }
  return tags.slice(0, 3);
}

function formatDate(d) {
  const date     = new Date(d);
  const datePart = date.toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric',
  }).toUpperCase();
  const timePart = date.toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', hour12: true,
  });
  return `${datePart} • ${timePart}`;
}

export default function History() {
  const navigate                = useNavigate();
  const [searches, setSearches] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [sortDesc, setSortDesc] = useState(true);

  useEffect(() => {
    API.get('/search/history/')
      .then(r => setSearches(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (id) => {
    try {
      await API.delete('/search/history/' + id + '/');
      setSearches(prev => prev.filter(s => s.id !== id));
    } catch { alert('Failed to delete.'); }
  };

  const handleRerun = (s) => {
    const kws = parseKeywords(s.keywords);
    if (s.search_mode === 'keyword') {
      navigate('/', { state: { searchMode: 'keyword', keywords: kws, focus: s.focus } });
    } else {
      navigate('/', { state: { searchMode: 'abstract', abstract: s.abstract, focus: s.focus } });
    }
  };

  const sorted = [...searches].sort((a, b) => {
    const diff = new Date(b.created_at) - new Date(a.created_at);
    return sortDesc ? diff : -diff;
  });

  if (loading) return <div className="loading">Loading your research archive...</div>;

  return (
    <div className="history-page">

      {/* ── Header ── */}
      <div className="history-header animate-fade-up">
        <div className="history-header-left">
          <h1 className="history-title">Search History</h1>
          <p className="history-subtitle">
            Your intellectual trajectory, preserved. Review past queries and resume your
            exploration across the digital expanse of academic research.
          </p>
        </div>
        {searches.length > 1 && (
          <button className="history-sort-btn" onClick={() => setSortDesc(p => !p)}>
            {sortDesc ? '↓ Newest first' : '↑ Oldest first'}
          </button>
        )}
      </div>

      {/* ── List ── */}
      {sorted.length === 0 ? (
        <div className="history-empty">
          <div className="history-empty-icon">✦</div>
          <p>No searches yet. Start your first semantic exploration.</p>
          <button
            className="btn-primary"
            style={{width:'auto', marginTop:'1.5rem'}}
            onClick={() => navigate('/')}
          >
            Start Searching
          </button>
        </div>
      ) : (
        <div className="history-list animate-fade-up-1">
          {sorted.map((s, i) => {
            const isKeyword = s.search_mode === 'keyword';
            const kws       = parseKeywords(s.keywords);

            // ── Keyword mode card ──
            if (isKeyword) {
              return (
                <div key={s.id} className="hentry" style={{animationDelay:(i * 0.07) + 's'}}>

                  {/* Left */}
                  <div className="hentry-left">
                    <div className="hentry-date">
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{flexShrink:0}}>
                        <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2" opacity=".5"/>
                        <path d="M6 3.5V6l1.5 1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                      </svg>
                      {formatDate(s.created_at)}
                    </div>

                    {/* Mode badge */}
                    <div className="hentry-mode-badge hentry-mode-keyword">
                      <svg width="11" height="11" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                        <rect x="1" y="3" width="6" height="4" rx="2" fill="currentColor" opacity=".85"/>
                        <rect x="9" y="3" width="6" height="4" rx="2" fill="currentColor" opacity=".85"/>
                        <rect x="1" y="9" width="6" height="4" rx="2" fill="currentColor" opacity=".5"/>
                        <rect x="9" y="9" width="6" height="4" rx="2" fill="currentColor" opacity=".5"/>
                      </svg>
                      Keyword Search
                    </div>

                    <div className="hentry-title">
                      {kws.length > 0 ? `"${kws.join('  ·  ')}"` : '"Keyword Search"'}
                    </div>

                    {/* Keyword chips */}
                    {kws.length > 0 && (
                      <div className="hentry-keyword-chips">
                        {kws.map((kw, ki) => (
                          <span key={ki} className="hentry-keyword-chip">{kw}</span>
                        ))}
                      </div>
                    )}

                    {s.focus && s.focus !== 'General / Best Fit' && (
                      <div className="hentry-tags">
                        <span className="hentry-tag">{s.focus.split('/')[0].trim().toUpperCase()}</span>
                      </div>
                    )}
                  </div>

                  {/* Right */}
                  <div className="hentry-right">
                    <button className="hentry-resume" onClick={() => handleRerun(s)}>RESUME →</button>
                    <button className="hentry-delete" onClick={() => handleDelete(s.id)}>Delete</button>
                  </div>

                </div>
              );
            }

            // ── Abstract mode card ──
            const tags    = extractTags(s.abstract, s.focus);
            const title   = '"' + (s.abstract.length > 80
              ? s.abstract.slice(0, 80) + '..."'
              : s.abstract + '"');
            const preview = s.abstract.length > 180
              ? s.abstract.slice(0, 180) + '...'
              : s.abstract;

            return (
              <div key={s.id} className="hentry" style={{animationDelay:(i * 0.07) + 's'}}>

                {/* Left */}
                <div className="hentry-left">
                  <div className="hentry-date">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{flexShrink:0}}>
                      <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2" opacity=".5"/>
                      <path d="M6 3.5V6l1.5 1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                    </svg>
                    {formatDate(s.created_at)}
                  </div>

                  {/* Mode badge */}
                  <div className="hentry-mode-badge hentry-mode-abstract">
                    <svg width="11" height="11" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                      <rect x="1" y="2" width="14" height="2" rx="1" fill="currentColor" opacity=".7"/>
                      <rect x="1" y="6" width="10" height="2" rx="1" fill="currentColor"/>
                      <rect x="1" y="10" width="12" height="2" rx="1" fill="currentColor" opacity=".7"/>
                      <rect x="1" y="14" width="7" height="2" rx="1" fill="currentColor" opacity=".4"/>
                    </svg>
                    Abstract Search
                  </div>

                  <div className="hentry-title">{title}</div>

                  <p className="hentry-preview">{preview}</p>

                  {tags.length > 0 && (
                    <div className="hentry-tags">
                      {tags.map(t => <span key={t} className="hentry-tag">{t}</span>)}
                    </div>
                  )}
                </div>

                {/* Right */}
                <div className="hentry-right">
                  <button className="hentry-resume" onClick={() => handleRerun(s)}>RESUME →</button>
                  <button className="hentry-delete" onClick={() => handleDelete(s.id)}>Delete</button>
                </div>

              </div>
            );
          })}
        </div>
      )}

      {/* ── End of history ── */}
      {sorted.length > 0 && (
        <div className="history-footer animate-fade-up-2">
          <span className="history-footer-icon">✦</span>
          <span className="history-footer-text">END OF CURATED HISTORY</span>
        </div>
      )}
    </div>
  );
}
