import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { VintageData } from '../types/api'
import { mw, pct, signed, utcShort } from '../utils/format'
import { COLORS } from './GenerationChart'

const tip = { contentStyle: { background: '#0f1f38', border: '1px solid #223555', fontSize: 12 } }

export function LeadTimeChart({ data }: { data: VintageData }) {
  const rows = data.by_lead_time.map((r) => ({ ...r, label: `≥${r.lead_hours}h` }))
  return (
    <div>
      <div role="img" aria-label="Bar chart of MAE and RMSE in megawatts by forecast lead time">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
            <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" />
            <XAxis dataKey="label" stroke={COLORS.axis} tick={{ fontSize: 11 }}
              label={{ value: 'Latest forecast published at least … before delivery', position: 'insideBottom', offset: -2, fill: COLORS.axis, fontSize: 11 }} height={40} />
            <YAxis stroke={COLORS.axis} tick={{ fontSize: 11 }} width={52} tickFormatter={(v) => mw(v)}
              label={{ value: 'Error (MW)', angle: -90, position: 'insideLeft', fill: COLORS.axis, fontSize: 11 }} />
            <Tooltip {...tip} formatter={(v, n) => [`${mw(v as number)} MW`, n]} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="mae" name="MAE" fill="#60a5fa" isAnimationActive={false} />
            <Bar dataKey="rmse" name="RMSE" fill="#34d399" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="table-wrap" style={{ maxHeight: 220, marginTop: 8 }}>
        <table>
          <thead><tr><th>Lead time</th><th>MAE (MW)</th><th>RMSE (MW)</th><th>Bias (MW)</th><th>n</th><th>Coverage</th></tr></thead>
          <tbody>
            {data.by_lead_time.map((r) => (
              <tr key={r.lead_hours}><td>≥ {r.lead_hours} h</td><td>{mw(r.mae)}</td><td>{mw(r.rmse)}</td><td>{signed(r.bias)}</td>
                <td>{mw(r.n)}</td><td>{pct(r.coverage_pct)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/** Each distinct publication (vintage): MAE vs. its publish time. Shows which runs fall before the cutoff. */
export function PublicationTable({ data }: { data: VintageData }) {
  const rows = data.by_publication
  if (!rows.length) return <div className="empty">No publications with enough matched hours in this scope.</div>
  return (
    <div className="table-wrap" style={{ maxHeight: 300 }}>
      <table>
        <thead><tr><th>Publication (UTC)</th><th>MAE (MW)</th><th>Bias (MW)</th><th>Mean lead (h)</th><th>n</th><th>Before cutoff</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.publish_utc}><td>{utcShort(r.publish_utc)}</td><td>{mw(r.mae)}</td><td>{signed(r.bias)}</td>
              <td>{mw(r.mean_lead_hours, 1)}</td><td>{mw(r.n)}</td><td>{pct(r.share_before_cutoff_pct, 0)}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
