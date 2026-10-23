import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Dashboard from '../pages/Dashboard'

const m = (o = {}) => ({ n: 744, eligible: 744, coverage_pct: 100, mae: 2127.48, rmse: 2606.07, bias: 1851.53, mape_pct: 22.2, n_mape: 744, nmae_pct: 18, ...o })
const row = (i: number, over = {}) => ({
  start_utc: `2026-01-01T0${i}:00:00Z`, start_local: `2026-01-01 0${i}:00`, settlement_date: '2026-01-01', settlement_period: i * 2 + 1,
  actual_mw: 1000, decision_forecast_mw: 1200, decision_publish_utc: '2025-12-31T07:30:00Z', latest_forecast_mw: 1100,
  latest_publish_utc: '2026-01-01T00:30:00Z', cutoff_utc: '2025-12-31T09:00:00Z', lead_hours: 20, error_mw: 200, abs_error_mw: 200,
  squared_error_mw2: 40000, status: 'matched', latest_postdates_cutoff: true, ...over,
})
const GEN = [row(1), row(2, { actual_mw: null, error_mw: null, abs_error_mw: null, status: 'no_actual' })]
const payloads: Record<string, unknown> = {
  '/api/v1/metadata': { window: { start: '2026-01-01', end: '2026-01-31' }, default_cutoff_local: '09:00', data_loaded: true, ingest_running: false,
    data_refreshed_at: '2026-01-05T10:00:00Z' },
  '/api/v1/summary': { decision_forecast: m(), latest_forecast: m({ mae: 1764 }), actual_periods: 1488, total_periods: 1488, mape_min_actual_mw: 100 },
  '/api/v1/generation': GEN,
  '/api/v1/errors': { metrics: m(), histogram: [{ from_mw: 0, to_mw: 500, count: 3 }], by_hour: [{ hour: 1, n: 3, mae: 10, bias: 2 }], by_day: [] },
  '/api/v1/forecast-vintages': { cutoff_local: '09:00', by_lead_time: [{ lead_hours: 6, ...m() }], by_publication: [] },
}

function mockFetch(overrides: Record<string, () => Response | Promise<Response>> = {}) {
  const fn = vi.fn((url: string) => {
    const path = url.split('?')[0]
    if (overrides[path]) return Promise.resolve(overrides[path]())
    return Promise.resolve(new Response(JSON.stringify({ meta: {}, data: payloads[path] }), { status: 200 }))
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

beforeEach(() => { class RO { observe() {} unobserve() {} disconnect() {} } vi.stubGlobal('ResizeObserver', RO) })
afterEach(() => { vi.unstubAllGlobals() })

describe('Dashboard', () => {
  it('shows loading skeletons first', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    render(<Dashboard />)
    expect(screen.getAllByRole('status').length).toBeGreaterThan(0)
  })

  it('renders KPIs with n/coverage and the table with missing values as dashes', async () => {
    mockFetch()
    render(<Dashboard />)
    const mae = await screen.findByRole('group', { name: /MAE/ })
    expect(mae).toHaveTextContent('2,127')
    expect(mae).toHaveTextContent('n = 744 of 744')
    expect(screen.getByRole('group', { name: /Mean bias/ })).toHaveTextContent('+1,852')
    expect((await screen.findAllByRole('table')).length).toBeGreaterThan(0)
    await waitFor(() => expect(screen.getAllByText('Actual missing').length).toBeGreaterThan(0))
    expect(screen.getAllByTitle(/not treated as zero/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Data refreshed 2026-01-05 10:00:00 UTC/)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Line chart of actual wind generation/ })).toBeInTheDocument()
  })

  it('shows API error and retries successfully', async () => {
    let fail = true
    mockFetch({ '/api/v1/summary': () => fail
      ? new Response(JSON.stringify({ error: { code: 'x', message: 'Data not loaded yet' } }), { status: 503 })
      : new Response(JSON.stringify({ meta: {}, data: payloads['/api/v1/summary'] }), { status: 200 }) })
    render(<Dashboard />)
    expect((await screen.findAllByText(/Data not loaded yet/))[0]).toBeInTheDocument()
    fail = false
    fireEvent.click(screen.getAllByRole('button', { name: 'Retry' })[0])
    expect(await screen.findByRole('group', { name: /MAE/ })).toBeInTheDocument()
  })

  it('shows empty state when there are no matched observations', async () => {
    mockFetch({ '/api/v1/summary': () => new Response(JSON.stringify({ meta: {}, data: {
      decision_forecast: m({ n: 0, coverage_pct: 0, mae: null }), latest_forecast: m({ n: 0 }), actual_periods: 0, total_periods: 48, mape_min_actual_mw: 100 } }), { status: 200 }) })
    render(<Dashboard />)
    expect(await screen.findByText(/No matched forecast\/actual periods/)).toBeInTheDocument()
  })

  it('date filter refetches with the chosen day and reset restores the month', async () => {
    const f = mockFetch()
    render(<Dashboard />)
    await screen.findByRole('group', { name: /MAE/ })
    fireEvent.change(screen.getByLabelText('From (delivery day)'), { target: { value: '2026-01-10' } })
    fireEvent.change(screen.getByLabelText('To'), { target: { value: '2026-01-10' } })
    await waitFor(() => expect(f.mock.calls.some(([u]) => String(u).includes('/summary?start=2026-01-10&end=2026-01-10'))).toBe(true))
    fireEvent.click(screen.getByRole('button', { name: 'Reset filters' }))
    await waitFor(() => expect(f.mock.calls.some(([u]) => String(u).includes('/summary?start=2026-01-01&end=2026-01-31'))).toBe(true))
  })
})
