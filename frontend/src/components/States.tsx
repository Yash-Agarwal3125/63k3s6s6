import type { ReactNode } from 'react'
import type { ApiState } from '../hooks/useApi'

export function Skeleton({ h = 200 }: { h?: number }) {
  return <div className="skeleton" style={{ height: h }} role="status" aria-label="Loading" />
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="err" role="alert">
      <span>⚠ {message}</span>
      <button className="btn" onClick={onRetry}>Retry</button>
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>
}

/** Renders loading / error / empty / content for one API state. */
export function Async<T>({ state, h, isEmpty, emptyText, children }: {
  state: ApiState<T>; h?: number; isEmpty?: (d: T) => boolean; emptyText?: string; children: (d: T) => ReactNode
}) {
  if (state.error) return <ErrorBox message={state.error} onRetry={state.retry} />
  if (state.loading || !state.data) return <Skeleton h={h} />
  if (isEmpty?.(state.data)) return <Empty>{emptyText ?? 'No data for the selected scope.'}</Empty>
  return <>{children(state.data)}</>
}

export function Card({ title, sub, children }: { title: string; sub?: ReactNode; children: ReactNode }) {
  return (
    <section className="card" aria-label={title}>
      <h2>{title}</h2>
      {sub && <div className="sub">{sub}</div>}
      {children}
    </section>
  )
}
