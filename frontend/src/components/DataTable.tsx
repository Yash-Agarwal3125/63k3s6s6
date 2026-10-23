import { useEffect, useState } from 'react'
import type { GenRow } from '../types/api'
import { mw, signed, STATUS_LABEL, utcShort } from '../utils/format'

const PAGE = 48
const NA = <span title="Not available - not treated as zero">—</span>

export function DataTable({ rows }: { rows: GenRow[] }) {
  const [status, setStatus] = useState('all')
  const [page, setPage] = useState(0)
  const shown = status === 'all' ? rows : rows.filter((r) => r.status === status)
  const pages = Math.max(1, Math.ceil(shown.length / PAGE))
  useEffect(() => setPage(0), [status, rows])
  const slice = shown.slice(page * PAGE, (page + 1) * PAGE)
  const cell = (v: number | null, f: (x: number) => string = (x) => mw(x)) => v == null ? <td className="na">{NA}</td> : <td>{f(v)}</td>
  return (
    <div>
      <div className="pager">
        <label className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>Availability status
          <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by availability status">
            <option value="all">All periods</option>
            {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <span className="sub">{mw(shown.length)} periods</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Delivery start (London)</th><th>SP</th><th>Decision forecast (MW)</th><th>Forecast published (UTC)</th>
              <th>Actual (MW)</th><th>Signed error (MW)</th><th>Abs error (MW)</th><th>Latest forecast (MW)</th><th>Status</th></tr>
          </thead>
          <tbody>
            {slice.map((r) => (
              <tr key={r.start_utc}>
                <td>{r.start_local}</td><td>{r.settlement_period}</td>
                {cell(r.decision_forecast_mw)}
                <td>{utcShort(r.decision_publish_utc)}</td>
                {cell(r.actual_mw)}{cell(r.error_mw, (x) => signed(x))}{cell(r.abs_error_mw)}{cell(r.latest_forecast_mw)}
                <td>{STATUS_LABEL[r.status] ?? r.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pager">
        <button className="btn" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
        <span>Page {page + 1} of {pages}</span>
        <button className="btn" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>Next</button>
      </div>
    </div>
  )
}
