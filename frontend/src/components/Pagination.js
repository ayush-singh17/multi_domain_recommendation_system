import { useMemo } from 'react';

export default function Pagination({ page, pageCount, onChange }) {
  const items = useMemo(() => {
    const wanted = new Set([1, pageCount, page - 1, page, page + 1]);
    if (page <= 3) [2, 3, 4].forEach(n => wanted.add(n));
    if (page >= pageCount - 2) [pageCount - 1, pageCount - 2, pageCount - 3].forEach(n => wanted.add(n));
    const nums = [...wanted].filter(n => n >= 1 && n <= pageCount).sort((a, b) => a - b);
    const out = [];
    nums.forEach((n, i) => {
      if (i > 0 && n - nums[i - 1] > 1) out.push(`gap-${n}`);
      out.push(n);
    });
    return out;
  }, [page, pageCount]);

  if (pageCount <= 1) return null;
  return (
    <nav className="rv2-pager" aria-label="Result pages">
      <button type="button" disabled={page === 1} onClick={() => onChange(page - 1)}>← Previous</button>
      <div className="rv2-pager-nums">
        {items.map(item => typeof item === 'string'
          ? <span key={item} className="rv2-pager-gap" aria-hidden="true">…</span>
          : <button key={item} type="button" className={item === page ? 'is-current' : ''}
              aria-current={item === page ? 'page' : undefined} onClick={() => onChange(item)}>{item}</button>)}
      </div>
      <button type="button" disabled={page === pageCount} onClick={() => onChange(page + 1)}>Next →</button>
    </nav>
  );
}
