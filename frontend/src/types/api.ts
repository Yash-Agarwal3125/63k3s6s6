export interface Envelope<T> { meta: Record<string, string>; data: T }

export interface Metrics {
  n: number; eligible: number; coverage_pct: number | null
  mae: number | null; rmse: number | null; bias: number | null
  mape_pct: number | null; n_mape: number; nmae_pct: number | null
}
export interface Summary {
  decision_forecast: Metrics; latest_forecast: Metrics
  actual_periods: number; total_periods: number; mape_min_actual_mw: number
}
export type Status =
  | 'matched' | 'no_half_hourly_forecast' | 'no_actual' | 'no_forecast_at_cutoff' | 'no_actual_no_forecast'
export interface GenRow {
  start_utc: string; start_local: string; settlement_date: string; settlement_period: number
  actual_mw: number | null; decision_forecast_mw: number | null; decision_publish_utc: string | null
  latest_forecast_mw: number | null; latest_publish_utc: string | null; cutoff_utc: string
  lead_hours: number | null; error_mw: number | null; abs_error_mw: number | null
  squared_error_mw2: number | null; status: Status; latest_postdates_cutoff: boolean
}
export interface ErrorsData {
  metrics: Metrics
  histogram: { from_mw: number; to_mw: number; count: number }[]
  by_hour: { hour: number; n: number; mae: number | null; bias: number | null }[]
  by_day: { date: string; n: number; mae: number | null; rmse: number | null; bias: number | null
    coverage_pct: number | null; mean_actual_mw: number | null; mean_forecast_mw: number | null }[]
}
export interface LeadRow extends Metrics { lead_hours: number }
export interface VintageData {
  cutoff_local: string
  by_lead_time: LeadRow[]
  by_publication: { publish_utc: string; n: number; mae: number | null; bias: number | null
    mean_lead_hours: number | null; share_before_cutoff_pct: number | null }[]
}
export interface Metadata {
  window: { start: string; end: string }; default_cutoff_local: string; data_loaded: boolean
  data_refreshed_at?: string; ingest_running: boolean
  coverage?: { delivery_days: number; expected_half_hour_periods: number; actual_periods_present: number
    actual_coverage_pct: number; missing_actual_periods: string[]; forecast_resolution: string
    hourly_targets: number; hourly_targets_with_decision_forecast: number; hourly_targets_with_any_forecast: number
    forecast_publications: number; forecast_records: number }
  assumptions?: string[]
}
export interface Filters { start: string; end: string; cutoff: string; basis: 'decision' | 'latest' }
