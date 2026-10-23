import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { GenRow } from '../types/api'
import { mw, utcShort } from '../utils/format'

export const COLORS = { actual: '#e6edf7', decision: '#34d399', latest: '#fbbf24', grid: '#223555', axis: '#93a4bf' }

/** Hourly-aligned rows only (WINDFOR resolution). Missing values stay null => visible gaps, never zero. */
export function GenerationChart({ rows }: { rows: GenRow[] }) {
  const data = rows.filter((r) => r.status !== 'no_half_hourly_forecast').map((r) => ({
    t: Date.parse(r.start_utc), actual: r.actual_mw, decision: r.decision_forecast_mw, latest: r.latest_forecast_mw,
    decPub: r.decision_publish_utc, latPub: r.latest_publish_utc, status: r.status,
  }))
  const multiDay = rows.length > 48 * 2
  const fmt = (t: number) => {
    const d = new Date(t)
    return multiDay
      ? d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })
      : d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })
  }
  return (
    <div role="img" aria-label="Line chart of actual wind generation, decision-time forecast and latest forecast in megawatts">
      <div className="legend-note">
        <span><i className="dot" style={{ background: COLORS.actual }} />Actual (FUELHH)</span>
        <span><i className="dot" style={{ background: COLORS.decision }} />Decision-time forecast</span>
        <span><i className="dot" style={{ background: COLORS.latest }} />Latest available forecast (hindsight)</span>
      </div>
      <ResponsiveContainer width="100%" height={340}>
        <LineChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
          <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" />
          <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={fmt}
            stroke={COLORS.axis} tick={{ fontSize: 11 }} label={{ value: 'Delivery time (UTC)', position: 'insideBottom', offset: -2, fill: COLORS.axis, fontSize: 11 }} height={40} />
          <YAxis stroke={COLORS.axis} tick={{ fontSize: 11 }} tickFormatter={(v) => mw(v)} width={56}
            label={{ value: 'MW', angle: -90, position: 'insideLeft', fill: COLORS.axis, fontSize: 11 }} />
          <Tooltip contentStyle={{ background: '#0f1f38', border: '1px solid #223555', fontSize: 12 }}
            labelFormatter={(t) => `${new Date(t as number).toISOString().slice(0, 16).replace('T', ' ')} UTC`}
            formatter={(v, name, p) => {
              const pub = name === 'Decision-time forecast' ? p.payload.decPub : name === 'Latest forecast' ? p.payload.latPub : null
              return [`${v == null ? '— (missing)' : mw(v as number) + ' MW'}${pub ? ` · pub ${utcShort(pub)}` : ''}`, name]
            }} />
          <Legend wrapperStyle={{ display: 'none' }} />
          <Line name="Actual" dataKey="actual" stroke={COLORS.actual} strokeWidth={1.8} dot={false} connectNulls={false} isAnimationActive={false} />
          <Line name="Decision-time forecast" dataKey="decision" stroke={COLORS.decision} strokeWidth={1.8} dot={false} connectNulls={false} isAnimationActive={false} />
          <Line name="Latest forecast" dataKey="latest" stroke={COLORS.latest} strokeWidth={1.4} strokeDasharray="5 3" dot={false} connectNulls={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
