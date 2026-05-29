const ROWS = [
  { label:'Quartile',      key: j => j.quartile },
  { label:'Risk Level',    key: j => j.risk_level },
  { label:'Relevance',     key: j => Math.round(j.final_score * 100) + '%' },
  { label:'SJR',           key: j => j.sjr ?? '—' },
  { label:'H-index',       key: j => j.h_index ?? '—' },
  { label:'CiteScore',     key: j => j.citescore ?? '—' },
  { label:'Impact Factor', key: j => j.impact_factor ?? '—' },
  { label:'Open Access',   key: j => j.open_access === 'Yes' ? 'Yes' : 'No' },
  { label:'APC',           key: j => j.apc_usd > 0 ? '~$'+j.apc_usd.toLocaleString() : j.open_access==='Yes' ? 'Free' : 'Subscription' },
  { label:'Avg. Time',     key: j => j.weeks_to_publish ? '~'+j.weeks_to_publish+'w' : '—' },
  { label:'Trend',         key: j => j.trend?.direction ? (j.trend.direction==='Up'?'↑':j.trend.direction==='Down'?'↓':'→')+' '+j.trend.direction : '—' },
  { label:'Publisher',     key: j => j.publisher ?? '—' },
  { label:'Coverage',      key: j => j.coverage ?? '—' },
  { label:'ISSN',          key: j => j.issn ?? '—' },
];

function bestColor(label, value, journals) {
  if (['SJR','H-index','CiteScore','Impact Factor','Relevance'].includes(label)) {
    const nums = journals.map(j => parseFloat(String(ROWS.find(r=>r.label===label)?.key(j)).replace('%','')));
    const max  = Math.max(...nums.filter(n => !isNaN(n)));
    const val  = parseFloat(String(value).replace('%',''));
    if (!isNaN(val) && val === max && max > 0) return 'var(--emerald)';
  }
  if (label === 'Risk Level') {
    if (value === 'Low')    return 'var(--emerald)';
    if (value === 'High')   return 'var(--rose)';
  }
  if (label === 'Avg. Time') {
    const nums = journals.map(j => parseFloat(String(ROWS.find(r=>r.label===label)?.key(j)).replace('~','').replace('w',''))).filter(n=>!isNaN(n));
    if (nums.length) {
      const min = Math.min(...nums);
      const val = parseFloat(String(value).replace('~','').replace('w',''));
      if (!isNaN(val) && val === min) return 'var(--emerald)';
    }
  }
  if (label === 'Trend') {
    if (value.includes('↑')) return 'var(--emerald)';
    if (value.includes('↓')) return 'var(--rose)';
  }
  return null;
}

export default function CompareModal({ journals, onClose }) {
  if (!journals?.length) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">Journal Comparison</div>
          <button className="modal-close" onClick={onClose}>✕ Close</button>
        </div>
        <div className="compare-scroll">
          <table className="compare-table">
            <thead>
              <tr>
                <th className="compare-th compare-th-label"></th>
                {journals.map((j,i) => (
                  <th key={i} className="compare-th compare-th-journal">
                    <div className="compare-journal-name">{j.title}</div>
                    <div className="compare-journal-plan">Plan {j._plan}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map(row => (
                <tr key={row.label} className="compare-row">
                  <td className="compare-td-label">{row.label}</td>
                  {journals.map((j,i) => {
                    const val   = String(row.key(j));
                    const color = bestColor(row.label, val, journals);
                    return (
                      <td key={i} className="compare-td-value" style={{color: color||undefined, fontWeight: color ? 600 : 400}}>
                        {val}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="modal-footer">
          Best values highlighted in <span style={{color:'var(--emerald)'}}>green</span>. Click outside to close.
        </div>
      </div>
    </div>
  );
}
