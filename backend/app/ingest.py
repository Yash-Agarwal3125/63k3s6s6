"""Idempotent ingestion of January 2026 wind actuals + forecast vintages."""
import json
import logging
import threading
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from . import db, elexon
from .config import Settings

log = logging.getLogger("ingest")
_lock = threading.Lock()


def is_running() -> bool:
    return _lock.locked()


def window_utc(s: Settings) -> tuple[datetime, datetime]:
    """[start, end) of the delivery window in UTC, using London local midnights."""
    tz = ZoneInfo(s.market_tz)
    a = datetime.combine(date.fromisoformat(s.window_start), time(0), tz).astimezone(timezone.utc)
    b = datetime.combine(date.fromisoformat(s.window_end) + timedelta(days=1), time(0), tz).astimezone(timezone.utc)
    return a, b


def run_ingest(s: Settings, client: elexon.ElexonClient) -> dict:
    """Fetch and upsert. Raises RuntimeError if another ingest is running."""
    if not _lock.acquire(blocking=False):
        raise RuntimeError("ingest already running")
    started = datetime.now(timezone.utc).strftime(elexon.TS_FMT)
    stats: dict = {}
    try:
        w0, w1 = window_utc(s)
        d0, d1 = date.fromisoformat(s.window_start), date.fromisoformat(s.window_end)
        raw_a = client.wind_actuals(d0, d1)
        act, bad_a = elexon.parse_actuals(raw_a)
        act = [r for r in act if w0.strftime(elexon.TS_FMT) <= r["start"] < w1.strftime(elexon.TS_FMT)]
        # dedupe: last record per start wins (source can republish)
        act = list({r["start"]: r for r in act}.values())

        f_raw = f_dup = 0
        fc, bad_f = [], []
        p = w0 - timedelta(days=s.forecast_lookback_days)
        p_end = w1 + timedelta(days=s.forecast_lookahead_days)
        lo, hi = w0.strftime(elexon.TS_FMT), w1.strftime(elexon.TS_FMT)
        while p < p_end:
            q = min(p + timedelta(days=2), p_end)
            rows = client.wind_forecasts(p, q)
            f_raw += len(rows)
            ok, bad = elexon.parse_forecasts(rows)
            fc += [r for r in ok if lo <= r["start"] < hi]  # restrict to January delivery
            bad_f += bad
            p = q
        uniq = {(r["start"], r["publish"]): r for r in fc}
        f_dup = len(fc) - len(uniq)
        fc = list(uniq.values())

        now = datetime.now(timezone.utc).strftime(elexon.TS_FMT)
        with db.connect(s.db_path) as con:
            db.upsert_actuals(con, act, now)
            db.upsert_forecasts(con, fc, now)
            stats = {
                "actual_source_rows": len(raw_a), "actual_wind_rows_kept": len(act), "actual_rejected": len(bad_a),
                "forecast_source_rows": f_raw, "forecast_rows_kept": len(fc),
                "forecast_duplicates_dropped": f_dup, "forecast_rejected": len(bad_f),
                "forecast_outside_january_dropped": f_raw - len(fc) - f_dup - len(bad_f),
                "rejected_examples": (bad_a + bad_f)[:5],
            }
            con.execute("INSERT INTO ingest_runs(started_at,finished_at,status,stats) VALUES(?,?,?,?)",
                        (started, now, "success", json.dumps(stats)))
        log.info("ingest ok %s", {k: v for k, v in stats.items() if k != "rejected_examples"})
        return stats
    except Exception as e:
        with db.connect(s.db_path) as con:
            con.execute("INSERT INTO ingest_runs(started_at,finished_at,status,error) VALUES(?,?,?,?)",
                        (started, datetime.now(timezone.utc).strftime(elexon.TS_FMT), "failed", str(e)[:500]))
        raise
    finally:
        _lock.release()
