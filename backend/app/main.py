"""FastAPI app. All responses: {"meta": {...}, "data": ...}."""
import hmac
import logging
import threading
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import analysis as A
from . import db, elexon, ingest
from .config import Settings, get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("api")
API = "/api/v1"


def _bg_ingest(s: Settings):
    try:
        ingest.run_ingest(s, elexon.ElexonClient(s.elexon_base_url, s.http_timeout_s))
    except Exception as e:  # failure is also recorded in ingest_runs
        log.error("background ingest failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    with db.connect(s.db_path) as con:
        empty = db.last_success(con) is None
    if empty and s.auto_ingest_on_empty:
        log.info("empty database: starting background ingest")
        threading.Thread(target=_bg_ingest, args=(s,), daemon=True).start()
    yield


app = FastAPI(title="UK Wind Day-Ahead Forecast Analytics", version="1.0.0", lifespan=lifespan,
              description="Elexon BMRS WINDFOR vs FUELHH(WIND), January 2026. Decision-time vs latest forecasts.")
app.add_middleware(CORSMiddleware, allow_origins=list(get_settings().cors_origins),
                   allow_methods=["GET", "POST"], allow_headers=["*"])


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    log.exception("unhandled error on %s", request.url.path)  # details stay in logs
    return JSONResponse({"error": {"code": "internal_error", "message": "Internal server error"}}, status_code=500)


@app.exception_handler(HTTPException)
async def _http(request: Request, exc: HTTPException):
    return JSONResponse({"error": {"code": f"http_{exc.status_code}", "message": str(exc.detail)}},
                        status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def _validation(request: Request, exc: RequestValidationError):
    msg = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
    return JSONResponse({"error": {"code": "validation_error", "message": msg}}, status_code=422)


class Scope:
    """Validated query scope shared by analysis endpoints."""

    def __init__(self, start: date | None = Query(None, description="First delivery date (London)"),
                 end: date | None = Query(None, description="Last delivery date, inclusive"),
                 cutoff: str | None = Query(None, description="Decision cutoff HH:MM Europe/London on D-1")):
        s = get_settings()
        w0, w1 = date.fromisoformat(s.window_start), date.fromisoformat(s.window_end)
        self.s = s
        self.start, self.end = start or w0, end or w1
        if self.start > self.end:
            raise HTTPException(422, "start must be <= end")
        if self.start < w0 or self.end > w1:
            raise HTTPException(422, f"dates must be within {w0}..{w1}")
        try:
            self.cutoff = A.parse_cutoff(cutoff or s.default_cutoff)
        except ValueError as e:
            raise HTTPException(422, str(e))
        with db.connect(s.db_path) as con:
            self.run = db.last_success(con)
        if self.run is None:
            raise HTTPException(503, "Data not loaded yet (initial ingestion in progress or failed). Retry shortly.")
        g, self.f, _ = A.frame(s, self.cutoff)
        self.g = A.in_range(g, self.start.isoformat(), self.end.isoformat())

    def meta(self) -> dict:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "cutoff_local": self.cutoff,
                "cutoff_rule": f"{self.cutoff} {self.s.market_tz} on the day before the delivery date (D-1)",
                "timezone_note": "Timestamps are UTC (ISO Z); *_local fields are Europe/London.",
                "data_refreshed_at": self.run["finished_at"]}


@app.get("/health")
def health():
    s = get_settings()
    with db.connect(s.db_path) as con:
        run = db.last_success(con)
    return {"status": "ok", "data_loaded": run is not None, "last_refresh": run and run["finished_at"],
            "ingest_running": ingest.is_running()}


@app.get(f"{API}/metadata")
def metadata():
    s = get_settings()
    with db.connect(s.db_path) as con:
        run = db.last_success(con)
        failed = con.execute(
            "SELECT finished_at,error FROM ingest_runs WHERE status='failed' ORDER BY id DESC LIMIT 1").fetchone()
    base = {"window": {"start": s.window_start, "end": s.window_end}, "default_cutoff_local": s.default_cutoff,
            "market_timezone": s.market_tz, "ingest_running": ingest.is_running(), "data_loaded": run is not None,
            "last_failed_refresh": dict(failed) if failed else None}
    if run is None:
        return {"meta": {}, "data": base}
    g, f, _ = A.frame(s, s.default_cutoff)
    miss = g[g.actual.isna()]
    h = g[g.hourly]
    base.update({
        "data_refreshed_at": run["finished_at"], "ingest_stats": run["stats"],
        "coverage": {
            "delivery_days": int(g.settlement_date.nunique()),
            "expected_half_hour_periods": int(len(g)), "actual_periods_present": int(g.actual.notna().sum()),
            "actual_coverage_pct": A._r(100 * g.actual.notna().mean()),
            "missing_actual_periods": [A._ts(x) for x in miss.start][:200],
            "forecast_resolution": "hourly (WINDFOR targets at :00 only); :30 periods have no forecast",
            "hourly_targets": int(len(h)),
            "hourly_targets_with_decision_forecast": int(h.dec_fc.notna().sum()),
            "hourly_targets_with_any_forecast": int(h.lat_fc.notna().sum()),
            "forecast_publications": int(f.publish.nunique()), "forecast_records": int(len(f)),
            "first_publication_utc": A._ts(f.publish.min()), "last_publication_utc": A._ts(f.publish.max())},
        "assumptions": [
            f"Decision cutoff = {s.default_cutoff} {s.market_tz} on D-1 (configurable; exact gate closure not verified from a primary source).",
            "Elexon timestamps are UTC; delivery day = Europe/London calendar day (identical to UTC in January).",
            "WINDFOR is hourly; no interpolation to half-hours.",
            "FUELHH WIND and WINDFOR may differ in scope (e.g. embedded/curtailed wind); bias may reflect definitions."],
        "sources": [
            {"dataset": "FUELHH", "filter": "fuelType=WIND", "fields": ["startTime", "generation"],
             "use": "actual generation (MW)"},
            {"dataset": "WINDFOR", "fields": ["startTime", "publishTime", "generation"],
             "use": "forecast vintages (MW)"}],
        "base_url": s.elexon_base_url})
    return {"meta": {}, "data": base}


@app.get(f"{API}/summary")
def summary(sc: Scope = Depends()):
    return {"meta": sc.meta(), "data": {
        "decision_forecast": A.series_metrics(sc.g, "dec_fc", sc.s),
        "latest_forecast": A.series_metrics(sc.g, "lat_fc", sc.s),
        "actual_periods": int(sc.g.actual.notna().sum()), "total_periods": int(len(sc.g)),
        "mape_min_actual_mw": sc.s.mape_min_actual_mw}}


@app.get(f"{API}/generation")
def generation(sc: Scope = Depends()):
    return {"meta": sc.meta(), "data": A.generation_rows(sc.g, sc.s.market_tz)}


@app.get(f"{API}/errors")
def errors(sc: Scope = Depends(), forecast: str = Query("decision", pattern="^(decision|latest)$"),
           bin_mw: int = Query(500, ge=50, le=5000)):
    col = "dec_fc" if forecast == "decision" else "lat_fc"
    return {"meta": {**sc.meta(), "forecast": forecast},
            "data": {"metrics": A.series_metrics(sc.g, col, sc.s), **A.error_breakdown(sc.g, col, sc.s, bin_mw)}}


@app.get(f"{API}/forecast-vintages")
def vintages(sc: Scope = Depends()):
    return {"meta": sc.meta(), "data": A.vintage_analysis(sc.g, sc.f, sc.s, sc.cutoff)}


@app.post(f"{API}/refresh", status_code=202)
def refresh(x_refresh_token: str = Header("")):
    s = get_settings()
    if not s.refresh_token:
        raise HTTPException(403, "Refresh is disabled (REFRESH_TOKEN not configured).")
    if not hmac.compare_digest(x_refresh_token, s.refresh_token):
        raise HTTPException(401, "Invalid refresh token.")
    if ingest.is_running():
        raise HTTPException(409, "A refresh is already running.")
    threading.Thread(target=_bg_ingest, args=(s,), daemon=True).start()
    return {"meta": {}, "data": {"status": "started", "started_at": datetime.now(timezone.utc).isoformat()}}
