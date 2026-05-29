// SubmissionTimeline — renders a dynamic roadmap from the currently-visible
// filtered journals. When no journals are visible it shows a clear empty state
// instead of vanishing silently.

export default function SubmissionTimeline({ timeline, totalShowing }) {
  const planColors = { A: 'var(--indigo)', B: 'var(--emerald)', C: 'var(--amber)' };
  const planNames  = { A: 'Reach Tier',   B: 'Strategic Tier', C: 'Safety Tier'  };

  const scenarioConfig = {
    optimistic: {
      cls:          'sc-optimistic',
      icon:         '🎯',
      color:        'var(--emerald)',
      total_bg:     'rgba(61,220,151,.12)',
      total_border: 'rgba(61,220,151,.3)',
      desc: 'Best case — Plan A accepts on first submission. No revision rounds needed.',
    },
    realistic: {
      cls:          'sc-realistic',
      icon:         '📋',
      color:        'var(--indigo)',
      total_bg:     'rgba(124,140,255,.12)',
      total_border: 'rgba(124,140,255,.3)',
      desc: 'Most likely outcome — one rejection from Plan A, one revision cycle, then accepted at Plan B.',
    },
    worst_case: {
      cls:          'sc-worst',
      icon:         '⏳',
      color:        'var(--amber)',
      total_bg:     'rgba(224,176,74,.12)',
      total_border: 'rgba(224,176,74,.3)',
      desc: 'Worst case — rejections cascade through all tiers with revision rounds between each submission.',
    },
  };

  // ── Empty state: no journals visible ──────────────────────────────────────
  if (!timeline || totalShowing === 0 || timeline.advice === null) {
    return (
      <div className="timeline-card timeline-empty">
        <div className="timeline-eyebrow">AI Strategy Roadmap</div>
        <h2 className="timeline-heading" style={{ marginBottom: '.75rem' }}>
          How long will this take?
        </h2>
        <div className="timeline-empty-body">
          <div className="timeline-empty-icon">📭</div>
          <p className="timeline-empty-msg">
            No journals are visible with the current filters.<br />
            Clear or relax your filters to restore the roadmap.
          </p>
        </div>
      </div>
    );
  }

  const { per_plan, scenarios, advice } = timeline;

  // ── Partial state: some plans are empty (e.g. only Plan C remains) ─────────
  const visiblePlans = Object.entries(per_plan).filter(([, v]) => v !== null);

  return (
    <div className="timeline-card">

      {/* Header */}
      <div className="timeline-eyebrow">AI Strategy Roadmap</div>
      <h2 className="timeline-heading">How long will this take?</h2>
      <p className="timeline-advice">{advice}</p>

      {/* Per-plan time cards — only visible plans */}
      <div className="timeline-plans">
        {visiblePlans.map(([key, plan]) => (
          <div key={key} className={'timeline-plan-card plan-' + key.toLowerCase()}>
            <div className="tpc-label" style={{ color: planColors[key] }}>
              Plan {key} — {planNames[key]}
            </div>
            <div className="tpc-time">{plan.display}</div>
            <div className="tpc-source">
              {plan.is_estimated ? 'Estimated from quartile avg.' : 'DOAJ publisher data'}
            </div>
          </div>
        ))}
      </div>

      {/* Scenario cards — only rendered when at least two plans exist */}
      {Object.keys(scenarios).length > 0 && (
        <>
          <div className="timeline-scenarios-heading">Submission Scenarios</div>

          <div className="timeline-scenarios">
            {Object.entries(scenarios).map(([key, sc]) => {
              const cfg = scenarioConfig[key] || scenarioConfig.realistic;
              return (
                <div key={key} className={'scenario-card ' + cfg.cls}>

                  {/* Header row */}
                  <div className="scenario-header">
                    <div className="scenario-label" style={{ color: cfg.color }}>
                      {cfg.icon} {sc.label}
                    </div>
                    <div
                      className="scenario-total"
                      style={{
                        background:  cfg.total_bg,
                        color:       cfg.color,
                        borderColor: cfg.total_border,
                      }}
                    >
                      Total: {sc.display}
                    </div>
                  </div>

                  {/* Step-by-step flow */}
                  <div className="scenario-steps">
                    {sc.steps.map((step, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '.35rem' }}>
                        {i > 0 && <span className="step-arrow">→</span>}

                        {step.action === 'Revise' ? (
                          <div className="step-revise">
                            ✏ Revise &amp; Resubmit
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '.68rem', marginLeft: '.3rem' }}>
                              {step.weeks}w
                            </span>
                          </div>
                        ) : (
                          <div className="scenario-step">
                            <div
                              className="step-badge"
                              style={{
                                background: planColors[step.plan] + '20',
                                color:      planColors[step.plan],
                                border:     '1px solid ' + planColors[step.plan] + '40',
                              }}
                            >
                              {step.plan}
                            </div>
                            <span className="step-journal" title={step.journal}>
                              {step.journal}
                            </span>
                            <span className="step-weeks">{step.weeks}w</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Human-readable description */}
                  <div className="scenario-desc">{cfg.desc}</div>

                </div>
              );
            })}
          </div>
        </>
      )}

      <div className="timeline-note">
        Times marked "Estimated from quartile" are averages — not from publisher data.
        DOAJ times are self-reported and may differ significantly from actual review timelines.
      </div>
    </div>
  );
}
