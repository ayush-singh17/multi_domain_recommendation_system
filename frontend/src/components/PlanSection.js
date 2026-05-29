import JournalCard from './JournalCard';

const PLAN_META = {
  A: { name: 'Plan A: High Impact Aggressive', desc: 'Top-tier Q1 journals. Maximum visibility, highest competition.', tip: 'Submit first', letter: 'a' },
  B: { name: 'Plan B: Balanced Tier',          desc: 'Strong Q2 journals with better acceptance odds.',              tip: 'If A is rejected', letter: 'b' },
  C: { name: 'Plan C: Safety Net',             desc: 'Indexed lower-tier journals. Faster turnaround.',              tip: 'Final fallback', letter: 'c' },
};

export default function PlanSection({ plan, journals, onCompareToggle, compareList }) {
  const meta = PLAN_META[plan];
  if (!journals || journals.length === 0) return null;

  return (
    <div className="plan-section">
      <div className="plan-header">
        <div className={'plan-letter plan-letter-' + meta.letter}>{plan}</div>
        <div>
          <div className="plan-name">{meta.name}</div>
          <div className="plan-desc">{meta.desc}</div>
        </div>
        <div className="plan-tip">{meta.tip}</div>
      </div>
      <div className="plan-journals">
        {journals.map((j, i) => (
          <JournalCard
            key={j.issn || i}
            journal={{ ...j, _plan: plan }}
            planKey={plan}
            onCompareToggle={onCompareToggle}
            isCompared={compareList?.some(c => c.issn === j.issn)}
          />
        ))}
      </div>
    </div>
  );
}
