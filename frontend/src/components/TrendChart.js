import { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts';

// ── Custom tooltip — light theme ──────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#FFFFFF',
      border: '1px solid #E2E8F0',
      borderRadius: 8,
      padding: '.6rem .9rem',
      fontSize: '.8rem',
      boxShadow: '0 4px 16px rgba(0,0,0,.08)',
    }}>
      <div style={{ color: '#64748B', marginBottom: 4, fontWeight: 600 }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.color, display: 'flex', gap: '.5rem', alignItems: 'center' }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: p.color, flexShrink: 0 }} />
          <span style={{ color: '#475569' }}>{p.name}:</span>
          <strong style={{ color: '#0F172A' }}>{p.value?.toFixed(2) ?? 'N/A'}</strong>
        </div>
      ))}
    </div>
  );
};

// ── Journal size label ────────────────────────────────────────────────────────
function journalSizeInfo(docs) {
  if (!docs) return null;
  if (docs > 500) return { label: 'Large journal',    color: '#0369A1', bg: '#EFF6FF' };
  if (docs > 100) return { label: 'Mid-size journal', color: '#92400E', bg: '#FFFBEB' };
  return              { label: 'Niche journal',       color: '#065F46', bg: '#ECFDF5' };
}

export default function TrendChart({ issn, title }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen]       = useState(false);
  const [error, setError]     = useState('');

  const fetchTrends = async () => {
    if (data) { setOpen(o => !o); return; }
    setLoading(true); setError('');
    try {
      const cleanIssn = issn?.split(',')[0].trim().replace(/-/g, '') || '';
      const res  = await fetch(`http://localhost:8001/trends/${cleanIssn}`);
      if (!res.ok) throw new Error('not found');
      const json = await res.json();

      const chartData = json.years.map((year, i) => ({
        year:            String(year),
        'Citations/Doc': json.citations?.[i] ?? null,
        'SJR':           json.sjr?.[i]        ?? null,
      }));

      setData({ ...json, chartData });
      setOpen(true);
    } catch {
      setError('Trend data not available for this journal.');
      setOpen(true);
    } finally {
      setLoading(false);
    }
  };

  const dir        = data?.trend_direction;
  const trendUp    = dir === 'Up';
  const trendDown  = dir === 'Down';
  const trendColor = trendUp ? '#059669' : trendDown ? '#DC2626' : '#D97706';
  const trendBg    = trendUp ? '#ECFDF5' : trendDown ? '#FEF2F2' : '#FFFBEB';
  const trendBorder= trendUp ? '#A7F3D0' : trendDown ? '#FECACA' : '#FDE68A';
  const trendIcon  = trendUp ? '↑' : trendDown ? '↓' : '→';
  const trendLabel = trendUp ? 'Trending Up' : trendDown ? 'Trending Down' : 'Stable';
  const pct = data?.trend_pct != null && Math.abs(data.trend_pct) < 1000
    ? ` ${data.trend_pct > 0 ? '+' : ''}${Number(data.trend_pct).toFixed(1)}% (2020→2024)`
    : '';

  const lastDocs = data?.docs?.[data.docs.length - 1];
  const lastYear = data?.years?.[data.years.length - 1];
  const sizeInfo = journalSizeInfo(lastDocs);

  return (
    <div style={{ marginTop: '.85rem' }}>

      {/* Toggle button */}
      <button onClick={fetchTrends} className="trend-toggle-btn">
        {loading ? 'Loading...' : open ? '▲ Hide Trend' : '📈 Show 5-Year Trend'}
      </button>

      {open && (
        <div style={{
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: 12,
          padding: '1.1rem 1.25rem',
          marginTop: '.4rem',
          boxShadow: '0 2px 8px rgba(0,0,0,.05)',
        }}>
          {error ? (
            <div style={{ color: '#94A3B8', fontSize: '.82rem', textAlign: 'center', padding: '1rem 0' }}>
              {error}
            </div>
          ) : data && (
            <>
              {/* Header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '.75rem', marginBottom: '1.1rem', flexWrap: 'wrap' }}>
                <span style={{
                  background: trendBg,
                  border: `1px solid ${trendBorder}`,
                  color: trendColor,
                  borderRadius: 6,
                  padding: '.25rem .75rem',
                  fontSize: '.78rem',
                  fontWeight: 700,
                }}>
                  {trendIcon} {trendLabel}{pct}
                </span>
                <span style={{ color: '#94A3B8', fontSize: '.8rem' }}>
                  Citations per document (2-year window)
                </span>
              </div>

              {/* Citations/Doc chart */}
              <div style={{
                fontSize: '.6rem', fontWeight: 700,
                letterSpacing: '.12em', textTransform: 'uppercase',
                color: '#94A3B8', marginBottom: '.5rem',
              }}>
                Citations / Doc
              </div>
              <ResponsiveContainer width="100%" height={150}>
                <LineChart data={data.chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="year" tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line
                    type="monotone" dataKey="Citations/Doc"
                    stroke="#0369A1" strokeWidth={2.5}
                    dot={{ fill: '#0369A1', r: 4, strokeWidth: 0 }}
                    activeDot={{ r: 6, fill: '#0369A1', stroke: '#EFF6FF', strokeWidth: 2 }}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>

              {/* SJR chart */}
              <div style={{
                fontSize: '.6rem', fontWeight: 700,
                letterSpacing: '.12em', textTransform: 'uppercase',
                color: '#94A3B8', margin: '.9rem 0 .5rem',
              }}>
                SJR Score
              </div>
              <ResponsiveContainer width="100%" height={140}>
                <LineChart data={data.chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="year" tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line
                    type="monotone" dataKey="SJR"
                    stroke="#0D9488" strokeWidth={2.5}
                    dot={{ fill: '#0D9488', r: 4, strokeWidth: 0 }}
                    activeDot={{ r: 6, fill: '#0D9488', stroke: '#F0FDFA', strokeWidth: 2 }}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>

              {/* Journal size footer */}
              {sizeInfo && lastDocs != null && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '.5rem',
                  marginTop: '.85rem', paddingTop: '.75rem',
                  borderTop: '1px solid #F1F5F9',
                  fontSize: '.78rem', color: '#64748B',
                }}>
                  <span style={{ fontWeight: 600 }}>Journal size ({lastYear ?? 2024}):</span>
                  <span>{lastDocs.toLocaleString()} docs/year</span>
                  <span style={{ color: '#CBD5E1' }}>—</span>
                  <span style={{
                    background: sizeInfo.bg,
                    color: sizeInfo.color,
                    fontWeight: 700,
                    fontSize: '.72rem',
                    padding: '.15rem .55rem',
                    borderRadius: 4,
                  }}>
                    {sizeInfo.label}
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
