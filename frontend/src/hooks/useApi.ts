import { useCallback, useEffect, useState } from 'react'
import type { Envelope } from '../types/api'

export interface ApiState<T> {
  data: T | null
  meta: Record<string, string> | null
  loading: boolean
  error: string | null
  retry: () => void
}

/** Fetches on mount and whenever `key` changes; `retry` refetches. Stale responses are ignored. */
export function useApi<T>(fn: () => Promise<Envelope<T>>, key: string): ApiState<T> {
  const [s, setS] = useState<Omit<ApiState<T>, 'retry'>>({ data: null, meta: null, loading: true, error: null })
  const [nonce, setNonce] = useState(0)
  useEffect(() => {
    let live = true
    setS((p) => ({ ...p, loading: true, error: null }))
    fn().then(
      (r) => live && setS({ data: r.data, meta: r.meta, loading: false, error: null }),
      (e: Error) => live && setS({ data: null, meta: null, loading: false, error: e.message }),
    )
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, nonce])
  const retry = useCallback(() => setNonce((n) => n + 1), [])
  return { ...s, retry }
}
