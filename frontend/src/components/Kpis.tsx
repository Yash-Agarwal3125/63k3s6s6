import type { ApiState } from '../hooks/useApi'
import type { Metrics, Summary } from '../types/api'
import { mw, pct, signed } from '../utils/format'
import { Async, Skeleton } from './States'

function Kpi({ label, value, unit, foot, note }: { label: string; value: string; unit?: string; foot: string; note?: string }) {
  return (
    <div className="card kpi" role="group" aria-label={label}>
      <div className="label">{label}</div>
      <div className="value">{value} {unit && <small>{unit}</small>}</div>
      <div className="foot">{foot}</div>
      {note && <div className="foot">{note}</div>}
    </div>
  )
}

const nFoot = (m: Metrics) => `n = ${mw(m.n)} of ${mw(m.eligible)} hourly periods (${pct(m.coverage_pct)})`

export function Kpis({ state }: { state: ApiState<Summary> }) {
  return (
    <div className="grid kpis">
      <Async state={state} h={110} isEmpty={(s) => s.decision_forecast.n === 0}
        emptyText="No matched forecast/actual periods in this scope."
        children={(s) => {
          const d = s.decision_forecast, l = s.latest_forecast
          return (
            <>
              <Kpi label="MAE · decision-time forecast" value={mw(d.mae)} unit="MW" foot={nFoot(d)} note={`Latest forecast: ${mw(l.mae)} MW`} />
              <Kpi label="RMSE · decision-time forecast" value={mw(d.rmse)} unit="MW" foot={nFoot(d)} note={`Latest forecast: ${mw(l.rmse)} MW`} />
              <Kpi label="Mean bias · decision-time" value={signed(d.bias)} unit="MW"
                foot={d.bias == null ? '' : d.bias > 0 ? 'Positive = over-forecast (forecast − actual)' : 'Negative = under-forecast (forecast − actual)'}
                note={`Latest forecast: ${signed(l.bias)} MW`} />
              <Kpi label="Data coverage" value={pct(d.coverage_pct)} foot={`${mw(d.n)} matched of ${mw(d.eligible)} eligible hourly periods`}
                note={`${mw(s.actual_periods)} of ${mw(s.total_periods)} half-hour actuals present`} />
            </>
          )
        }} />
      {state.loading && !state.data && [1, 2, 3].map((i) => <Skeleton key={i} h={110} />)}
    </div>
  )
}
