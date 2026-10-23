# Technical walkthrough

## 1. Repository tour
`backend/app/config.py` (env settings, frozen dataclass) · `elexon.py` (HTTP client, retry/backoff, record validation) · `db.py` (SQLite schema/upserts) · `ingest.py` (windowed fetch → upsert, run log, lock) · `analysis.py` (selection + metrics) · `main.py` (routes). `frontend/src`: `api/client.ts` (typed fetch), `hooks/useApi.ts`, `components/*`, `pages/Dashboard.tsx`, `test/`. Root: `docker-compose.yml`, `docs/`.

## 2. Architecture
Elexon → ingestion → SQLite → pandas analysis on request (cached per ingest) → FastAPI JSON → React. The UI never recomputes metrics.

## 3. Data pipeline
`ElexonClient._get` retries 429/5xx/transport errors with exponential backoff and rejects non-list payloads. `parse_actuals` keeps `fuelType == WIND`, `parse_forecasts` validates timestamps/values; rejects are counted and sampled. `run_ingest` fetches actuals once and forecasts in 2-day publish windows (±4 days around January), keeps January targets, dedupes on `(start, publish)`, bulk `INSERT OR REPLACE`, and writes an `ingest_runs` row. A module lock makes a second concurrent run fail fast (HTTP 409 at the endpoint).

## 4. Critical algorithm (`analysis._frame_cached`)
1. Build the 1,488-slot UTC grid from London midnights.
2. `cutoff = (London date − 1 day) + HH:MM`, localised to Europe/London → UTC (`decision_cutoff_utc`).
3. Merge forecasts on `start`; keep `publish <= cutoff`; sort by publish; `groupby(start).tail(1)` → decision forecast, its publish time, lead hours.
4. Independently take the max-publish forecast → latest.
5. Status column: `no_half_hourly_forecast`, `no_actual`, `no_forecast_at_cutoff`, `no_actual_no_forecast`, `matched`.
6. `metrics()` uses only rows where both actual and forecast exist.

## 5. API walkthrough
`/health`, `/api/v1/metadata` (coverage, assumptions, provenance), `/summary` (decision and latest metrics), `/generation` (row-level audit data incl. publish times and `latest_postdates_cutoff`), `/errors` (histogram, by hour, by day), `/forecast-vintages` (lead-time and per-publication), `POST /refresh` (token-protected). Shared `Scope` dependency validates dates (inside January), `start<=end` and `cutoff` format.

## 6. Frontend structure
`Dashboard` owns filter state and five `useApi` calls keyed by filter values (stale responses ignored). `Async` renders skeleton / error+retry / empty / content. Charts: `GenerationChart`, `VintageCharts`, `ErrorCharts`; `DataTable` (status filter, pagination, "—" for null).

## 7. Tests
Backend: `cd backend && pytest -q` (23). Frontend: `cd frontend && npm test` (5, fetch mocked). Lint/type: `ruff check .`, `npm run lint`, `npm run typecheck`.

## 8. Docker and deployment
Backend image (python slim, non-root, healthcheck, `/data` volume). Frontend image builds with Node and serves via nginx with `/api` proxied to `backend`. See SUBMISSION_CHECKLIST.md for what is actually deployed.

## 9. Known limitations and next steps
Assumed cutoff; hourly forecast resolution; possible FUELHH/WINDFOR scope difference; one month; no scheduled refresh; SQLite single-instance.
