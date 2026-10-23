export const mw = (v: number | null | undefined, digits = 0): string =>
  v == null ? '—' : v.toLocaleString('en-GB', { maximumFractionDigits: digits, minimumFractionDigits: digits })
export const signed = (v: number | null | undefined, digits = 0): string =>
  v == null ? '—' : (v > 0 ? '+' : '') + mw(v, digits)
export const pct = (v: number | null | undefined, digits = 1): string => (v == null ? '—' : `${mw(v, digits)}%`)
export const utcShort = (iso: string | null): string => (iso ? iso.replace('T', ' ').replace(/:00Z$/, ' UTC').replace(/Z$/, ' UTC') : '—')
export const dayLabel = (d: string): string =>
  new Date(d + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })
export const STATUS_LABEL: Record<string, string> = {
  matched: 'Matched',
  no_half_hourly_forecast: 'No half-hourly forecast',
  no_actual: 'Actual missing',
  no_forecast_at_cutoff: 'No forecast at cutoff',
  no_actual_no_forecast: 'No data',
}
