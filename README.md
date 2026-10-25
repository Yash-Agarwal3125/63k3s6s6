# UK Wind Day-Ahead Forecast Analytics

Web application for a UK electricity utility's day-ahead desk. It answers: *"Which national wind forecast could we actually see before the day-ahead decision, and how accurate was it against realised wind generation in January 2026?"*

**Live demo:** https://63k3s6s6.vercel.app  |  **API:** https://wind-api-y73h.onrender.com/health  |  **Source:** https://github.com/Yash-Agarwal3125/63k3s6s6  |  **Demo video:** https://youtu.be/QLfqTOV066g

> The API runs on a free Render instance that sleeps when idle. If the dashboard shows "Cannot reach the analytics API", wait about a minute and press Retry.

All data comes from the **Elexon BMRS API only** (`WINDFOR` forecasts, `FUELHH` actuals). No demand, price, weather or other generation data is used.

## Features
- **Decision-time vs latest forecast**, kept strictly separate: the decision-time forecast is the latest `publishTime` at/before a configurable D-1 cutoff; the latest forecast may contain later information and is shown for comparison only.
- KPIs (MAE, RMSE, mean bias, coverage) with observation counts beside every metric; MAPE (guarded for near-zero actuals) and normalised MAE in the API.
- Actual vs forecast time-series, error histogram, MAE by delivery hour, daily MAE/bias.
- **Vintage analysis:** accuracy by lead time (≥1h … ≥48h) and per-publication accuracy.
- Half-hourly table (48 periods/day) with availability status; missing values show "—", never zero.
- Day/range/cutoff filters with reset; skeleton, error+retry and empty states; data-freshness badge.
- Residual-demand explainer (directional only) and methodology/limitations panel.

## Architecture
```mermaid
flowchart LR
  E[Elexon BMRS API<br/>WINDFOR + FUELHH] -->|httpx, retries| I[Ingestion<br/>validate, dedupe, upsert]
  I --> D[(SQLite)]
  D --> A[Analysis<br/>cutoff selection + metrics<br/>pandas]
  A --> API[FastAPI /api/v1]
  API -->|JSON| UI[React + Recharts<br/>nginx / Vercel]
```
More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Data sources
| Dataset | Filter | Fields used | Notes |
|---|---|---|---|
| `FUELHH` | `fuelType=WIND` | `startTime`, `generation` (MW), `settlementDate`, `settlementPeriod` | half-hourly actuals |
| `WINDFOR` | by `publishDateTime` window | `startTime`, `publishTime`, `generation` (MW) | **hourly** targets; ~8 publications/day, each ~73h ahead |

Endpoints used (no key required): `GET /datasets/FUELHH/stream?settlementDateFrom&settlementDateTo&fuelType=WIND` and `GET /datasets/WINDFOR/stream?publishDateTimeFrom&publishDateTimeTo` under `https://data.elexon.co.uk/bmrs/api/v1`. Forecasts are fetched from 4 days before to 4 days after January so December publications and post-delivery vintages are available.

## Decision cutoff and publication times
Default cutoff: **09:00 Europe/London on D-1** (env `DECISION_CUTOFF`, or the *Decision cutoff* filter). This is an **assumption**: the exact gate-closure/auction deadline was not verified from a primary source. For delivery day D, a forecast is eligible iff `publishTime <= cutoff(D)`; the eligible forecast with the greatest `publishTime` is selected per delivery hour. See [docs/DATA_METHODOLOGY.md](docs/DATA_METHODOLOGY.md).

## Metrics
With `e = forecast − actual` over periods where both exist (n): MAE = mean(|e|); RMSE = √mean(e²); mean bias = mean(e) (positive = over-forecast); MAPE = mean(|e|/|actual|) over actuals ≥ 100 MW (count reported as `n_mape`); NMAE = MAE / mean(actual). Coverage = matched / eligible hourly periods.

## Limitations
- WINDFOR is hourly: metrics use the 744 hourly (:00) periods; the 744 :30 periods have actuals but no forecast and are never interpolated.
- Cutoff is assumed. FUELHH vs WINDFOR scope may differ (embedded/curtailed wind), so bias may partly reflect definitions.
- Not a procurement tool: no demand, prices, positions or savings are computed.
- January 2026 only. Elexon revises/republishes data; results reflect the last successful refresh.

## Repository layout
```
backend/app/{config,elexon,db,ingest,analysis,main}.py   settings, API client+validation, SQLite, ingestion, selection+metrics, FastAPI
backend/tests/test_core.py                                23 tests (mocked HTTP, fixture DB)
backend/Dockerfile, requirements*.txt
frontend/src/{api,hooks,types,utils,styles,components,pages,test}   React + TS (Vite), Recharts
frontend/Dockerfile, nginx.conf, vercel.json
docker-compose.yml, render.yaml, .env.example
docs/                                                     ARCHITECTURE.md, DATA_METHODOLOGY.md
```

## Prerequisites
Docker Desktop (for compose), or Python 3.10+ and Node 20+ for local dev.

## Run with Docker
```bash
cp .env.example .env     # optional
docker compose up --build
# UI: http://localhost:8080   API docs: http://localhost:8000/docs
```
On first start the backend ingests January 2026 from Elexon in the background (~30–60 s; the UI shows an error/retry until data is loaded). Data persists in the `wind-data` volume. Host caveat: Docker Desktop must be running (on Windows start it first).

## Run without Docker
```bash
# backend
cd backend && python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
# frontend (new shell)
cd frontend && npm install && npm run dev      # http://localhost:5173 (proxies /api to :8000)
```

## Environment variables
See `.env.example` (all optional): `ELEXON_BASE_URL`, `DB_PATH`, `DECISION_CUTOFF`, `MARKET_TZ`, `WINDOW_START/END`, `FORECAST_LOOKBACK_DAYS/LOOKAHEAD_DAYS`, `HTTP_TIMEOUT_S`, `MAPE_MIN_ACTUAL_MW`, `REFRESH_TOKEN`, `AUTO_INGEST_ON_EMPTY`, `CORS_ORIGINS`, and frontend `VITE_API_BASE_URL`.

## API
All responses are `{"meta": {...}, "data": ...}`; errors are `{"error": {"code", "message"}}`. Shared query params: `start`, `end` (YYYY-MM-DD, within January 2026), `cutoff` (HH:MM London).
```bash
curl localhost:8000/health
curl localhost:8000/api/v1/metadata
curl "localhost:8000/api/v1/summary?start=2026-01-15&end=2026-01-15&cutoff=09:00"
curl "localhost:8000/api/v1/generation?start=2026-01-15&end=2026-01-15"
curl "localhost:8000/api/v1/errors?forecast=latest"        # forecast=decision|latest
curl "localhost:8000/api/v1/forecast-vintages"
curl -X POST localhost:8000/api/v1/refresh -H "X-Refresh-Token: $REFRESH_TOKEN"   # 403 unless REFRESH_TOKEN set; 409 if running
```
Interactive docs at `/docs`.

## Tests and quality
```bash
cd backend && pytest -q && ruff check .
cd frontend && npm run typecheck && npm run lint && npm test && npm run build
```

## Deployment
- Frontend: Vercel (root `frontend`, preset Vite, env `VITE_API_BASE_URL` = backend URL).
- Backend: Render web service from `render.yaml` (Docker, free plan). Set `CORS_ORIGINS` to the Vercel origin.
- The free Render instance sleeps after inactivity (first request ~50 s) and has no disk, so SQLite is rebuilt from Elexon on start (`AUTO_INGEST_ON_EMPTY`). Add a persistent disk on a paid plan to keep the database between restarts.

## Troubleshooting
- *UI shows "Data not loaded yet"*: first ingest still running; retry in a minute, or check `/health`.
- *Docker "cannot connect to daemon"*: start Docker Desktop.
- *CORS error in a split deployment*: add the frontend origin to `CORS_ORIGINS`.
- *Refresh returns 403*: set `REFRESH_TOKEN`.

## AI tools disclosure
This project was built with **Claude Code** (Anthropic, model Claude Sonnet 5.5) acting as the coding agent for research, implementation, tests and documentation. No other AI coding tools were used. All numbers shown come from the real Elexon data; metric output was cross-checked against an independent recomputation from raw API responses.

## Future improvements
Verify the gate-closure time from market rules; multiple cutoff scenarios side by side; half-hourly forecast alignment as an explicit option; scheduled refresh; auth for refresh; more months.
