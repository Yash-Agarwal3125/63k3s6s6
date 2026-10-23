import type { Metadata } from '../types/api'
import { mw, pct } from '../utils/format'
import { Card } from './States'

export function ResidualPanel() {
  return (
    <Card title="What forecast error means for residual demand" sub="Explanatory only — no demand, price or procurement data is used or calculated.">
      <div className="prose">
        <p>A simplified view: <code>residual demand = demand − wind − other included generation</code>. This prototype has <strong>no</strong> demand or other-generation data, so it does <strong>not</strong> calculate actual residual demand, the utility&apos;s procurement need, market prices or savings.</p>
        <ul>
          <li><strong>Wind under-forecast</strong> (forecast &lt; actual, negative error): the team may overestimate the additional power it needs to buy.</li>
          <li><strong>Wind over-forecast</strong> (forecast &gt; actual, positive error): the team may underestimate the additional power it needs to buy and be exposed to a shortfall.</li>
        </ul>
        <p>Demand forecasts, other supply, balancing actions, portfolio positions, market rules and contracts are out of scope.</p>
      </div>
    </Card>
  )
}

export function Methodology({ meta }: { meta: Metadata | null }) {
  const c = meta?.coverage
  return (
    <Card title="Methodology and limitations">
      <div className="prose">
        <ul>
          <li><strong>Sources (Elexon BMRS only):</strong> actuals from <code>FUELHH</code> filtered to <code>fuelType=WIND</code>; forecasts from <code>WINDFOR</code> (all publication vintages).</li>
          <li><strong>Decision-time forecast:</strong> for each delivery period, the forecast with the latest <code>publishTime</code> at or before the cutoff (default 09:00 Europe/London on D-1, an <em>assumption</em>, adjustable above). Later vintages are never used.</li>
          <li><strong>Latest available forecast:</strong> the most recent publication for that period, which can include information unavailable at decision time. Shown for comparison only.</li>
          <li><strong>Resolution:</strong> WINDFOR is hourly, so metrics use the 24 hourly (:00) periods per day; :30 actuals are shown in the table without a forecast. Nothing is interpolated or zero-filled.</li>
          <li><strong>Error</strong> = forecast − actual (positive = over-forecast). MAE, RMSE and bias are over periods with both values; MAPE excludes actuals below 100 MW.</li>
          <li><strong>Timezone:</strong> source timestamps are UTC; the delivery day is the Europe/London day (identical to UTC in January).</li>
          <li><strong>Caveat:</strong> FUELHH and WINDFOR may differ in scope (e.g. embedded or curtailed wind), so a persistent bias can partly reflect definitions rather than pure forecast skill.</li>
        </ul>
        {c && (
          <p className="sub">Dataset: {c.delivery_days} delivery days · {mw(c.actual_periods_present)} of {mw(c.expected_half_hour_periods)} half-hour actuals ({pct(c.actual_coverage_pct)}) ·
            {' '}{mw(c.hourly_targets_with_decision_forecast)} of {mw(c.hourly_targets)} hourly targets have a decision-time forecast · {mw(c.forecast_publications)} forecast publications / {mw(c.forecast_records)} records.</p>
        )}
      </div>
    </Card>
  )
}
