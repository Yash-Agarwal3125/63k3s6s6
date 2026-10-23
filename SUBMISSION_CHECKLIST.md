# Submission checklist

Only items actually verified are ticked. Verified on 2026-10-23 on the author's Windows machine.

## Automated / engineering
- [ ] Public GitHub repository verified (see final report for URL; tick after you open it in incognito)
- [ ] Public frontend URL verified — **NOT DEPLOYED** (Vercel/Heroku CLIs not installed or authenticated)
- [ ] Public backend health URL verified — **NOT DEPLOYED**
- [x] January 2026 data retrieval verified (1,488 actuals; 744 hourly targets; 18,104 forecast records; 272 publications)
- [x] Data coverage and missing records documented (docs/DATA_METHODOLOGY.md, `/api/v1/metadata`)
- [x] Docker build and startup verified (`docker compose up --build`; UI :8080, API :8000 healthy, data ingested into volume)
- [x] Backend tests passing (23) and frontend tests passing (5)
- [x] Lint (ruff, eslint) and type check (tsc) passing
- [x] Production builds passing (frontend `npm run build`, Docker images)
- [x] No secrets committed (no tokens/keys exist in the repo; `.env` ignored)
- [x] README and architecture documents complete

## Deployment — how to finish (shortest path)
1. Backend: create a Render (or Fly/Railway) web service from this repo using `render.yaml` (Docker, root `backend`), attach a disk at `/data`, set `CORS_ORIGINS=https://<your-vercel-domain>`. Wait for `/health` to show `data_loaded: true`.
2. Frontend: `cd frontend && npx vercel` (log in), set env `VITE_API_BASE_URL=https://<backend-url>`, `npx vercel --prod`.
3. Open both URLs in incognito; add them to README "Deployment".

## Yours to do (not done by Claude)
- [ ] Customer demo recorded by me (script: docs/CUSTOMER_DEMO_GUIDE.md Part 1)
- [ ] Technical review video recorded by me (docs/CUSTOMER_DEMO_GUIDE.md Part 2, docs/TECHNICAL_WALKTHROUGH.md)
- [ ] Videos uploaded as unlisted YouTube videos by me
- [ ] Both YouTube links tested in a private/incognito browser session
- [ ] Submission form completed by me
- [ ] Every submitted URL opened and verified in incognito mode
