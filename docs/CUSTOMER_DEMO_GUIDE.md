# Demo guides

Scripts only — nothing here records or uploads video. Numbers below are from the real data at the default 09:00 D-1 cutoff; re-check on screen before speaking them.

## Part 1 — Customer presentation (5:00)

**0:00–0:30 Problem and value.** "Wind swings by gigawatts with the weather. Before the day-ahead auction you must estimate how much power to buy after wind. This tool shows exactly which wind forecast you could see at decision time, and how wrong it was against what really generated — so you can size the uncertainty you carry into the auction."

**0:30–1:30 Dashboard and headline metrics.** Open the full-month view. Point at the four KPIs: MAE ≈ 2,127 MW, RMSE ≈ 2,606 MW, mean bias ≈ +1,852 MW (over-forecast), coverage 100% (744 of 744 hourly periods). Stress the footer under each card: n and coverage are always shown. Note the freshness badge (data refreshed at …) and the blue notice defining decision-time vs latest.

**1:30–2:30 Actuals vs decision-time forecast.** Scroll to the main chart. White = actual, green = decision-time forecast, amber dashed = latest forecast (published later, hindsight — not available when you decide). Hover a point to show the publication timestamp. Switch to a single day with the date inputs (e.g. 15 Jan: MAE ≈ 1,025 MW decision-time vs ≈ 689 MW latest). Open the table: show the forecast-published column (07:30 UTC on D-1), blank "—" cells where data is missing, and the status column. Mention :30 periods have no forecast because the source is hourly.

**2:30–3:30 Error analysis and vintages.** Error distribution (skewed right = over-forecast), MAE by hour, daily MAE/bias. Then "Accuracy by lead time": MAE rises from ≈ 1,801 MW (≥1 h) to ≈ 2,380 MW (≥48 h) — fresher forecasts are better but the day-ahead decision is stuck with the D-1 vintage. Show per-publication table and the "before cutoff" share. Change the cutoff time to show sensitivity.

**3:30–4:30 Interpreting uncertainty.** Pick 28 Jan (worst day: forecast ≈ 11.1 GW vs actual ≈ 5.8 GW mean, MAE ≈ 5.3 GW) versus 19 Jan (best, MAE ≈ 0.7 GW). Read the residual-demand panel: an over-forecast of wind means the team could *under*-buy; an under-forecast means *over*-buying. Say clearly: we do not have demand, prices or positions, so no cost or savings is claimed.

**4:30–5:00 Value, scope, next steps.** Value: auditable forecast-at-decision-time, quantified error and lead-time behaviour. Scope: one month, national wind, Elexon only, assumed cutoff. Next: confirm gate-closure time, bias investigation (scope differences), more months, residual-demand with demand data, scheduled refresh.

## Part 2 — Internal technical review (5:00)

**0:00–1:00 Architecture.** Repo tour: `backend/app` (config, elexon, db, ingest, analysis, main), `frontend/src`, compose, docs. Show the README mermaid diagram; stress the frontend only renders — metrics live in the backend.

**1:00–2:00 Data integrity.** `elexon.py` validation; `ingest.py` windows, dedupe, upsert, `ingest_runs` stats; show `/api/v1/metadata` coverage (1,488 actuals, 744 hourly targets, 272 publications, 0 rejected). Explain 3,721 post-target publications kept but never decision-eligible. Mention the independent 15 Jan recomputation.

**2:00–3:30 Algorithm.** `analysis._frame_cached`: full January grid, per-slot cutoff (London D-1 09:00 → UTC), merge, `publish <= cutoff`, sort, `groupby.tail(1)`; latest selected separately; statuses via `np.select`; `metrics()` on matched pairs only. Show the boundary test (publish exactly at cutoff eligible, +1 s excluded) and BST cutoff test.

**3:30–4:30 Tests.** `pytest` (23 backend tests: parsing, WIND filter, timezone, selection, missing data, MAPE zero handling, ingest idempotence/dedupe via mocked HTTP, retries, API validation/shape, health, refresh auth); `npm test` (5 frontend tests: loading, success, error+retry, empty, filter+reset); ruff, eslint, tsc, build.

**4:30–5:00 Deployment.** Docker compose (nginx → FastAPI, SQLite volume, healthchecks). State honestly what is and isn't deployed publicly (see SUBMISSION_CHECKLIST.md), the assumptions, and next steps.
