import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ErrorsData } from '../types/api'
import { dayLabel, mw, signed } from '../utils/format'
import { COLORS } from './GenerationChart'

const tip = { contentStyle: { background: '#0f1f38', border: '1px solid #223555', fontSize: 12 } }
const axis = { stroke: COLORS.axis, tick: { fontSize: 11 } }
const yl = (v: string) => ({ value: v, angle: -90, position: 'insideLeft' as const, fill: COLORS.axis, fontSize: 11 })
const xl = (v: string) => ({ value: v, position: 'insideBottom' as const, offset: -2, fill: COLORS.axis, fontSize: 11 })

export function ErrorHistogram({ d }: { d: ErrorsData }) {
  const rows = d.histogram.map((b) => ({ label: `${(b.from_mw + b.to_mw) / 2}`, count: b.count, from: b.from_mw, to: b.to_mw }))
  return (
    <div role="img" aria-label="Histogram of signed forecast error (forecast minus actual) in megawatts">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" />
          <XAxis dataKey="label" {...axis} height={40} label={xl('Forecast − actual (MW), bin centre; >0 = over-forecast')} />
          <YAxis {...axis} width={44} label={yl('Periods')} allowDecimals={false} />
          <Tooltip {...tip} labelFormatter={(_, p) => (p[0] ? `${signed(p[0].payload.from)} to ${signed(p[0].payload.to)} MW` : '')}
            formatter={(v) => [`${v} periods`, 'Count']} />
          <ReferenceLine x="0" stroke={COLORS.latest} />
          <Bar dataKey="count" fill="#60a5fa" isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ErrorByHour({ d }: { d: ErrorsData }) {
  return (
    <div role="img" aria-label="Bar chart of mean absolute error in megawatts by delivery hour">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={d.by_hour} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" />
          <XAxis dataKey="hour" {...axis} height={40} label={xl('Delivery hour (Europe/London)')} />
          <YAxis {...axis} width={52} tickFormatter={(v) => mw(v)} label={yl('MAE (MW)')} />
          <Tooltip {...tip} labelFormatter={(h) => `Hour ${String(h).padStart(2, '0')}:00`}
            formatter={(v, n, p) => [`${mw(v as number)} MW (n=${p.payload.n}, bias ${signed(p.payload.bias)})`, n]} />
          <Bar dataKey="mae" name="MAE" fill="#34d399" isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ErrorByDay({ d }: { d: ErrorsData }) {
  const rows = d.by_day.map((r) => ({ ...r, label: dayLabel(r.date) }))
  return (
    <div role="img" aria-label="Line chart of daily mean absolute error and bias in megawatts">
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" />
          <XAxis dataKey="label" {...axis} height={40} interval="preserveStartEnd" label={xl('Delivery day')} />
          <YAxis {...axis} width={52} tickFormatter={(v) => mw(v)} label={yl('MW')} />
          <ReferenceLine y={0} stroke={COLORS.axis} strokeDasharray="2 2" />
          <Tooltip {...tip} formatter={(v, n) => [`${v == null ? '—' : mw(v as number)} MW`, n]} />
          <Line dataKey="mae" name="Daily MAE" stroke="#34d399" dot={false} isAnimationActive={false} />
          <Line dataKey="bias" name="Daily bias" stroke="#fbbf24" dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
