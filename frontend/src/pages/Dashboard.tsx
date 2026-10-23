import { useState } from 'react'
import { api } from '../api/client'
import { DataTable } from '../components/DataTable'
import { ErrorByDay, ErrorByHour, ErrorHistogram } from '../components/ErrorCharts'
import { DEFAULT_FILTERS, FilterBar } from '../components/Filters'
import { GenerationChart } from '../components/GenerationChart'
import { Methodology, ResidualPanel } from '../components/Info'
import { Kpis } from '../components/Kpis'
import { Header, Sidebar } from '../components/Layout'
import { Async, Card } from '../components/States'
import { LeadTimeChart, PublicationTable } from '../components/VintageCharts'
import { useApi } from '../hooks/useApi'
import type { Filters } from '../types/api'
import { dayLabel } from '../utils/format'

export default function Dashboard() {
  const [f, setF] = useState<Filters>(DEFAULT_FILTERS)
  const k = `${f.start}|${f.end}|${f.cutoff}`
  const meta = useApi(() => api.metadata(), 'meta')
  const summary = useApi(() => api.summary(f), k)
  const gen = useApi(() => api.generation(f), k)
  const errors = useApi(() => api.errors(f), `${k}|${f.basis}`)
  const vint = useApi(() => api.vintages(f), k)
  const scope = f.start === f.end ? dayLabel(f.start) : `${dayLabel(f.start)} – ${dayLabel(f.end)}`
  const basisLabel = f.basis === 'decision' ? 'Decision-time forecast' : 'Latest available forecast'

  return (
    <div className="app">
      <Sidebar />
      <main className="main">
        <Header meta={meta.data} error={meta.error} />
        <FilterBar value={f} onChange={setF} />
        <div className="notice info" role="note">
          <strong>Decision-time forecast</strong> = latest WINDFOR publication at or before {f.cutoff} Europe/London on the day before delivery (assumed cutoff).
          {' '}<strong>Latest forecast</strong> may contain information published after that decision and is shown only for comparison.
        </div>
        <section id="overview" aria-label="Headline metrics"><Kpis state={summary} /></section>

        <section id="forecasts" className="section">
          <Card title={`Actual vs forecast · ${scope} 2026`} sub="Hourly delivery periods (WINDFOR resolution). Gaps = missing data, never zero.">
            <Async state={gen} h={380} isEmpty={(r) => r.length === 0}
              children={(rows) => <GenerationChart rows={rows} />} />
          </Card>
        </section>

        <section id="vintages" className="section">
          <h2>Forecast vintages and lead time</h2>
          <div className="grid cols-2">
            <Card title="Accuracy by lead time" sub="Latest forecast published at least N hours before delivery, over the selected scope.">
              <Async state={vint} h={300} isEmpty={(d) => d.by_lead_time.every((r) => r.n === 0)} children={(d) => <LeadTimeChart data={d} />} />
            </Card>
            <Card title="Accuracy by publication" sub={`Each WINDFOR publication in scope. "Before cutoff" = share of its targets published at/before the ${f.cutoff} D-1 cutoff.`}>
              <Async state={vint} h={300} children={(d) => <PublicationTable data={d} />} />
            </Card>
          </div>
        </section>

        <section id="errors" className="section">
          <h2>Forecast error analysis</h2>
          <div className="filters" style={{ marginBottom: 10 }}>
            <label className="field">Error basis
              <select value={f.basis} onChange={(e) => setF({ ...f, basis: e.target.value as Filters['basis'] })} aria-label="Error basis">
                <option value="decision">Decision-time forecast</option>
                <option value="latest">Latest available forecast</option>
              </select>
            </label>
            <span className="sub">Showing: {basisLabel}</span>
          </div>
          <div className="grid cols-2">
            <Card title="Error distribution" sub={`${basisLabel}: forecast − actual (MW)`}>
              <Async state={errors} h={280} isEmpty={(d) => d.metrics.n === 0} children={(d) => <ErrorHistogram d={d} />} />
            </Card>
            <Card title="MAE by delivery hour" sub={`${basisLabel}`}>
              <Async state={errors} h={280} isEmpty={(d) => d.metrics.n === 0} children={(d) => <ErrorByHour d={d} />} />
            </Card>
          </div>
          <div style={{ marginTop: 14 }}>
            <Card title="Daily MAE and bias" sub={`${basisLabel}, per delivery day`}>
              <Async state={errors} h={280} isEmpty={(d) => d.metrics.n === 0} children={(d) => <ErrorByDay d={d} />} />
            </Card>
          </div>
        </section>

        <section id="table" className="section">
          <Card title="Half-hourly periods" sub="Times in Europe/London; publication times in UTC. SP = settlement period. — = not available (not zero).">
            <Async state={gen} h={300} isEmpty={(r) => r.length === 0} children={(rows) => <DataTable rows={rows} />} />
          </Card>
        </section>

        <section id="method" className="section grid cols-2">
          <ResidualPanel />
          <Methodology meta={meta.data} />
        </section>
      </main>
    </div>
  )
}
