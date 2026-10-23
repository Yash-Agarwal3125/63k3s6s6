# Data methodology

## Datasets (verified by calling the live API)
- **FUELHH** `/datasets/FUELHH/stream` with `settlementDateFrom/To` and `fuelType=WIND`. Rows: `startTime` (UTC), `settlementDate`, `settlementPeriod`, `fuelType`, `generation` (MW), `publishTime`. 1,488 rows for January (31 × 48).
- **WINDFOR** `/datasets/WINDFOR/stream` with `publishDateTimeFrom/To`. Rows: `startTime` (target, UTC), `publishTime`, `generation` (MW). Targets are **hourly (:00)**; each publication covers roughly 73 hourly targets; ≈8 publications/day (e.g. 02:30, 04:30, 07:30, 09:30, 11:30, 15:30 … UTC). Filtering by `startTime` is not supported by the stream endpoint, so we filter by publish window and restrict targets to January locally. No authentication was required at time of build; no rate-limit headers were observed (429/5xx are retried anyway).
- `generation` is MW (power), compared directly; an hourly-target forecast is compared with the half-hourly actual at the same `startTime` (:00 slot).

## Ingestion
Actuals in one call; forecasts in 2-day publish windows from 4 days before to 4 days after January. Each record is validated (parseable UTC timestamp, numeric non-negative generation); non-WIND rows are filtered; January-only targets kept; duplicates collapsed on key; upserted with `INSERT OR REPLACE`. Result counts (actual/forecast rows seen, kept, rejected, duplicates, out-of-window) are stored per run in `ingest_runs.stats`.
Last real run: 1,488 actuals kept; 22,776 forecast rows seen; 18,104 kept (744 targets, 272 publications, 2025-12-30 02:30Z … 2026-02-01 22:30Z); 0 rejected; 4,672 outside January dropped. 3,721 kept forecast records were published *after* their own target time — they are retained (they feed only the "latest" series) and can never be decision-eligible.

## Timezones
Source timestamps are UTC (`Z`). Internally everything is tz-aware UTC. Delivery day / settlement date = Europe/London calendar day, which equals UTC throughout January (GMT). Cutoff conversion uses `zoneinfo`, so BST dates would convert correctly (unit-tested for July) even though the scope is January. Settlement period numbering follows the London day (48 per day in January); DST-day irregularities (46/50 periods) are out of scope.

## Decision cutoff (assumption)
`cutoff(D) = (D − 1 day) at HH:MM Europe/London`, default 09:00. I could not confirm the operational gate closure from an authoritative primary document, so this is an explicit, configurable assumption, labelled in the UI and `/metadata`. GB day-ahead auctions close in the morning of D-1; the user can change the cutoff in the filter bar to test sensitivity.

## Vintage selection
Per hourly delivery slot: eligible = forecasts with `publishTime ≤ cutoff` (equality eligible); selected = max `publishTime`. If none eligible, status `no_forecast_at_cutoff` and the value is null. "Latest" = max `publishTime` overall. `lead_hours = startTime − selected publishTime`. With the 09:00 cutoff, the selected publication is 07:30Z on D-1 and lead times run 16.5–39.5 h.

## Matching
Joins are on exact `startTime`. A forecast is never compared with another period's actual. Half-hour (:30) slots have no forecast (`no_half_hourly_forecast`) and are excluded from metrics and coverage denominators.

## Metrics
`e = forecast − actual`. MAE, RMSE, mean bias, MAPE (actual ≥ `MAPE_MIN_ACTUAL_MW`, default 100 MW; `n_mape` reported), NMAE = MAE / mean(actual) over matched pairs. Coverage = matched pairs / eligible hourly slots in scope. Also: 500 MW error histogram, by-hour and by-day breakdowns, lead-time table (latest forecast with `publish ≤ start − L h`, L ∈ {1,3,6,12,18,24,30,36,48}) and per-publication MAE.

## Missing data & validation
Missing values are null end-to-end (never zero). Coverage and the missing actual periods are in `/api/v1/metadata`. January actual coverage: 100% (1,488/1,488). Decision forecast coverage: 744/744 hourly targets at 09:00; at much earlier cutoffs some targets may lose coverage (e.g. lead ≥ 48 h has 589/744). Validation: API results for 15 Jan were recomputed independently from raw Elexon responses and match (n=24, MAE 1025.21, RMSE 1168.06, bias +1025.21).

## Limitations
Assumed cutoff; WINDFOR/FUELHH scope may differ (observed persistent over-forecast of ≈ +1.85 GW mean could partly be definitional — e.g. embedded or curtailed wind — which we did not investigate with non-Elexon data); hourly vs half-hourly resolution; one month; Elexon can revise data after our refresh.
