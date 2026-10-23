import type { Filters as F } from '../types/api'

export const MONTH_START = '2026-01-01'
export const MONTH_END = '2026-01-31'
export const DEFAULT_FILTERS: F = { start: MONTH_START, end: MONTH_END, cutoff: '09:00', basis: 'decision' }

const addDays = (d: string, n: number) => {
  const x = new Date(d + 'T00:00:00Z')
  x.setUTCDate(x.getUTCDate() + n)
  return x.toISOString().slice(0, 10)
}

export function FilterBar({ value, onChange }: { value: F; onChange: (f: F) => void }) {
  const set = (p: Partial<F>) => onChange({ ...value, ...p })
  const single = value.start === value.end
  const bounded = (d: string) => (d < MONTH_START ? MONTH_START : d > MONTH_END ? MONTH_END : d)
  return (
    <div className="filters" role="search" aria-label="Filters">
      <label className="field">From (delivery day)
        <input type="date" min={MONTH_START} max={MONTH_END} value={value.start}
          onChange={(e) => e.target.value && set({ start: e.target.value, end: e.target.value > value.end ? e.target.value : value.end })} />
      </label>
      <label className="field">To
        <input type="date" min={MONTH_START} max={MONTH_END} value={value.end}
          onChange={(e) => e.target.value && set({ end: e.target.value, start: e.target.value < value.start ? e.target.value : value.start })} />
      </label>
      <label className="field">Decision cutoff (D-1, London)
        <input type="time" value={value.cutoff} onChange={(e) => e.target.value && set({ cutoff: e.target.value })} />
      </label>
      <div className="field">Quick select
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn" onClick={() => set({ start: MONTH_START, end: MONTH_END })}>Full month</button>
          <button className="btn" disabled={!single || value.start <= MONTH_START} aria-label="Previous day"
            onClick={() => set({ start: bounded(addDays(value.start, -1)), end: bounded(addDays(value.start, -1)) })}>◀</button>
          <button className="btn" disabled={!single || value.end >= MONTH_END} aria-label="Next day"
            onClick={() => set({ start: bounded(addDays(value.end, 1)), end: bounded(addDays(value.end, 1)) })}>▶</button>
          <button className="btn" onClick={() => set({ end: value.start })}>Single day</button>
        </div>
      </div>
      <button className="btn" onClick={() => onChange(DEFAULT_FILTERS)}>Reset filters</button>
    </div>
  )
}
