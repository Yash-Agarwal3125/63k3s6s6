import type { Metadata } from '../types/api'

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="6" fill="#0b1f3a" stroke="#223555" /><path d="M6 20c4-8 7 6 10-2s7-6 10-2" stroke="#34d399" strokeWidth="3" fill="none" /></svg>
        <div>Wind Day-Ahead<small>Forecast analytics</small></div>
      </div>
      <nav className="nav" aria-label="Sections">
        <a href="#overview">Overview</a><a href="#forecasts">Forecast vs actual</a><a href="#vintages">Vintages</a>
        <a href="#errors">Error analysis</a><a href="#table">Half-hourly data</a><a href="#method">Methodology</a>
      </nav>
    </aside>
  )
}

export function Header({ meta, error }: { meta: Metadata | null; error: string | null }) {
  const fresh = meta?.data_refreshed_at
  return (
    <header className="header">
      <div>
        <h1>GB wind generation: day-ahead forecast accuracy</h1>
        <div className="sub">Delivery days 1–31 January 2026 · Source: Elexon BMRS (WINDFOR, FUELHH) · National totals, MW</div>
      </div>
      <div>
        {error ? <span className="badge warn">Metadata unavailable</span>
          : fresh ? <span className="badge ok" title="Last successful ingestion from Elexon">Data refreshed {fresh.replace('T', ' ').replace('Z', ' UTC')}</span>
            : <span className="badge">{meta && !meta.data_loaded ? 'Initial data load in progress…' : 'Checking data freshness…'}</span>}
      </div>
    </header>
  )
}
