import type { Envelope, ErrorsData, Filters, GenRow, Metadata, Summary, VintageData } from '../types/api'

const BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

async function get<T>(path: string, params?: Record<string, string>): Promise<Envelope<T>> {
  const qs = params ? '?' + new URLSearchParams(params).toString() : ''
  let res: Response
  try {
    res = await fetch(`${BASE}${path}${qs}`)
  } catch {
    throw new ApiError('Cannot reach the analytics API. Check your connection and retry.', 0)
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`
    try { msg = (await res.json()).error?.message ?? msg } catch { /* non-JSON error body */ }
    throw new ApiError(msg, res.status)
  }
  return res.json()
}

const scope = (f: Filters) => ({ start: f.start, end: f.end, cutoff: f.cutoff })

export const api = {
  metadata: () => get<Metadata>('/api/v1/metadata'),
  summary: (f: Filters) => get<Summary>('/api/v1/summary', scope(f)),
  generation: (f: Filters) => get<GenRow[]>('/api/v1/generation', scope(f)),
  errors: (f: Filters) => get<ErrorsData>('/api/v1/errors', { ...scope(f), forecast: f.basis }),
  vintages: (f: Filters) => get<VintageData>('/api/v1/forecast-vintages', scope(f)),
}
