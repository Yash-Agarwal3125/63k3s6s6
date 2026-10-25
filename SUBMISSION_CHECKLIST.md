# Submission checklist

Only items actually verified are ticked. Verified on 2026-10-23 on the author's Windows machine.

## Automated / engineering
- [ ] Public GitHub repository verified (see final report for URL; tick after you open it in incognito)
- [x] Public frontend URL verified: https://63k3s6s6.vercel.app (loaded in Chrome 2026-10-25; filters, charts, table, error basis, pagination tested)
- [x] Public backend health URL verified: https://wind-api-y73h.onrender.com/health (`data_loaded: true`)
- [x] January 2026 data retrieval verified (1,488 actuals; 744 hourly targets; 18,104 forecast records; 272 publications)
- [x] Data coverage and missing records documented (docs/DATA_METHODOLOGY.md, `/api/v1/metadata`)
- [x] Docker build and startup verified (`docker compose up --build`; UI :8080, API :8000 healthy, data ingested into volume)
- [x] Backend tests passing (23) and frontend tests passing (5)
- [x] Lint (ruff, eslint) and type check (tsc) passing
- [x] Production builds passing (frontend `npm run build`, Docker images)
- [x] No secrets committed (no tokens/keys exist in the repo; `.env` ignored)
- [x] README and architecture documents complete

## Deployment
Done via Render (free, Docker, root `backend`) + Vercel (root `frontend`). Free Render instance sleeps (~50 s cold start) and re-ingests on restart.

## Yours to do (not done by Claude)
- [ ] Customer demo recorded by me (script: docs/CUSTOMER_DEMO_GUIDE.md Part 1)
- [ ] Technical review video recorded by me (docs/CUSTOMER_DEMO_GUIDE.md Part 2, docs/TECHNICAL_WALKTHROUGH.md)
- [ ] Videos uploaded as unlisted YouTube videos by me
- [ ] Both YouTube links tested in a private/incognito browser session
- [ ] Submission form completed by me
- [ ] Every submitted URL opened and verified in incognito mode
