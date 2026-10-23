"""Forecast selection at the decision cutoff + metrics. All analytical truth lives here.

Key rules
- Decision-time forecast for a delivery slot = forecast with the greatest publish time <= cutoff,
  where cutoff = (London delivery date - 1 day) at HH:MM London local time. Later vintages are never used.
- Latest forecast = greatest publish time overall (may post-date the decision, even the delivery).
- WINDFOR is hourly (:00 targets only). :30 slots have no forecast and are never interpolated.
- Missing values stay NaN/None; nothing is zero-filled.
"""
import re
from functools import lru_cache

import numpy as np
import pandas as pd

from . import db
from .config import Settings

LEADS_H = [1, 3, 6, 12, 18, 24, 30, 36, 48]
CUTOFF_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def parse_cutoff(v: str) -> str:
    if not CUTOFF_RE.match(v):
        raise ValueError("cutoff must be HH:MM (24h, Europe/London local time)")
    return v


def decision_cutoff_utc(start_utc: pd.Series, hhmm: str, tz: str) -> pd.Series:
    """Cutoff = previous London calendar day at hh:mm London time, as UTC."""
    h, m = int(hhmm[:2]), int(hhmm[3:])
    d = start_utc.dt.tz_convert(tz).dt.tz_localize(None).dt.normalize() - pd.Timedelta(days=1)
    local = d + pd.Timedelta(hours=h, minutes=m)
    return local.dt.tz_localize(tz, ambiguous=True, nonexistent="shift_forward").dt.tz_convert("UTC")


def _grid(s: Settings) -> pd.DatetimeIndex:
    tz = s.market_tz
    a = pd.Timestamp(s.window_start, tz=tz).tz_convert("UTC")
    b = (pd.Timestamp(s.window_end, tz=tz) + pd.Timedelta(days=1)).tz_convert("UTC")
    return pd.date_range(a, b, freq="30min", inclusive="left")


def _load(s: Settings):
    with db.connect(s.db_path) as con:
        a = pd.read_sql("SELECT start_utc, generation_mw AS actual FROM actuals", con)
        f = pd.read_sql("SELECT start_utc, publish_utc, generation_mw AS fc FROM forecasts", con)
        run = db.last_success(con)
    a["start"] = pd.to_datetime(a.pop("start_utc"), utc=True)
    f["start"] = pd.to_datetime(f.pop("start_utc"), utc=True)
    f["publish"] = pd.to_datetime(f.pop("publish_utc"), utc=True)
    return a, f, run


@lru_cache(maxsize=16)
def _frame_cached(version: int, s: Settings, cutoff: str):
    a, f, run = _load(s)
    g = pd.DataFrame({"start": _grid(s)})
    g["settlement_date"] = g.start.dt.tz_convert(s.market_tz).dt.strftime("%Y-%m-%d")
    g["period"] = g.groupby("settlement_date").cumcount() + 1
    g = g.merge(a[["start", "actual"]], on="start", how="left")
    g["cutoff"] = decision_cutoff_utc(g.start, cutoff, s.market_tz)
    g["hourly"] = g.start.dt.minute == 0  # forecast resolution
    m = f.merge(g[["start", "cutoff"]], on="start")
    sel = m[m.publish <= m.cutoff].sort_values("publish").groupby("start").tail(1)
    g = g.merge(sel[["start", "fc", "publish"]].rename(columns={"fc": "dec_fc", "publish": "dec_pub"}), on="start", how="left")
    lat = f.sort_values("publish").groupby("start").tail(1)
    g = g.merge(lat.rename(columns={"fc": "lat_fc", "publish": "lat_pub"}), on="start", how="left")
    g["lead_h"] = (g.start - g.dec_pub).dt.total_seconds() / 3600
    g["status"] = np.select(
        [~g.hourly, g.actual.isna() & g.dec_fc.isna(), g.actual.isna(), g.dec_fc.isna()],
        ["no_half_hourly_forecast", "no_actual_no_forecast", "no_actual", "no_forecast_at_cutoff"],
        "matched")
    return g, f, run


def frame(s: Settings, cutoff: str):
    """Returns (frame, forecasts, last_run). Cache is keyed on the last successful ingest id."""
    with db.connect(s.db_path) as con:
        r = con.execute("SELECT COALESCE(MAX(id),0) FROM ingest_runs WHERE status='success'").fetchone()[0]
    return _frame_cached(r, s, cutoff)


def in_range(g: pd.DataFrame, d0: str, d1: str) -> pd.DataFrame:
    return g[(g.settlement_date >= d0) & (g.settlement_date <= d1)]


def _r(x, n=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


def metrics(act: pd.Series, fc: pd.Series, eligible: int, mape_min: float) -> dict:
    """Metrics over rows where BOTH values exist. error = forecast - actual (positive = overforecast)."""
    ok = act.notna() & fc.notna()
    a, f = act[ok].to_numpy(float), fc[ok].to_numpy(float)
    n = int(ok.sum())
    base = {"n": n, "eligible": int(eligible), "coverage_pct": _r(100 * n / eligible) if eligible else None}
    if n == 0:
        return {**base, "mae": None, "rmse": None, "bias": None, "mape_pct": None, "n_mape": 0, "nmae_pct": None}
    e = f - a
    big = np.abs(a) >= mape_min
    return {**base,
            "mae": _r(np.mean(np.abs(e))), "rmse": _r(np.sqrt(np.mean(e**2))), "bias": _r(np.mean(e)),
            "mape_pct": _r(100 * np.mean(np.abs(e[big]) / np.abs(a[big]))) if big.any() else None,
            "n_mape": int(big.sum()),
            "nmae_pct": _r(100 * np.mean(np.abs(e)) / np.mean(a)) if np.mean(a) > 0 else None}


def series_metrics(g: pd.DataFrame, col: str, s: Settings) -> dict:
    return metrics(g.actual, g[col], int(g.hourly.sum()), s.mape_min_actual_mw)


def _ts(x):
    return None if pd.isna(x) else x.strftime("%Y-%m-%dT%H:%M:%SZ")


def generation_rows(g: pd.DataFrame, tz: str) -> list[dict]:
    out = []
    for r in g.itertuples():
        err = None if pd.isna(r.actual) or pd.isna(r.dec_fc) else r.dec_fc - r.actual
        out.append({
            "start_utc": _ts(r.start), "start_local": r.start.tz_convert(tz).strftime("%Y-%m-%d %H:%M"),
            "settlement_date": r.settlement_date, "settlement_period": int(r.period),
            "actual_mw": _r(r.actual, 1), "decision_forecast_mw": _r(r.dec_fc, 1), "decision_publish_utc": _ts(r.dec_pub),
            "latest_forecast_mw": _r(r.lat_fc, 1), "latest_publish_utc": _ts(r.lat_pub), "cutoff_utc": _ts(r.cutoff),
            "lead_hours": _r(r.lead_h), "error_mw": _r(err, 1), "abs_error_mw": _r(None if err is None else abs(err), 1),
            "squared_error_mw2": _r(None if err is None else err * err, 1), "status": r.status,
            "latest_postdates_cutoff": bool(not pd.isna(r.lat_pub) and r.lat_pub > r.cutoff)})
    return out


def error_breakdown(g: pd.DataFrame, col: str, s: Settings, bin_mw: int = 500) -> dict:
    m = g[g.actual.notna() & g[col].notna()].copy()
    m["err"] = m[col] - m.actual
    hist = []
    if len(m):
        lo = int(np.floor(m.err.min() / bin_mw) * bin_mw)
        hi = int(np.ceil((m.err.max() + 1e-9) / bin_mw) * bin_mw)
        edges = np.arange(lo, hi + bin_mw, bin_mw)
        cnt, _ = np.histogram(m.err, bins=edges)
        hist = [{"from_mw": int(edges[i]), "to_mw": int(edges[i + 1]), "count": int(c)} for i, c in enumerate(cnt)]
    m["hour"] = m.start.dt.tz_convert(s.market_tz).dt.hour
    by_hour = [{"hour": int(h), "n": int(len(x)), "mae": _r(x.err.abs().mean()), "bias": _r(x.err.mean())}
               for h, x in m.groupby("hour")]
    by_day = []
    for d, x in g.groupby("settlement_date"):
        mm = metrics(x.actual, x[col], int(x.hourly.sum()), s.mape_min_actual_mw)
        k = x[x.actual.notna() & x[col].notna()]
        by_day.append({"date": d, **{k_: mm[k_] for k_ in ("n", "mae", "rmse", "bias", "coverage_pct")},
                       "mean_actual_mw": _r(k.actual.mean()), "mean_forecast_mw": _r(k[col].mean())})
    return {"histogram": hist, "by_hour": by_hour, "by_day": by_day}


def vintage_analysis(g: pd.DataFrame, f: pd.DataFrame, s: Settings, cutoff: str) -> dict:
    """(a) accuracy by lead time: latest forecast published >= L hours before delivery.
    (b) accuracy of each individual publication (vintage) over the selected range."""
    h = g[g.hourly]
    elig = len(h)
    m = f.merge(h[["start", "actual", "cutoff"]], on="start")
    by_lead = []
    for L in LEADS_H:
        k = m[m.publish <= m.start - pd.Timedelta(hours=L)].sort_values("publish").groupby("start").tail(1)
        r = h[["start", "actual"]].merge(k[["start", "fc"]], on="start", how="left")
        by_lead.append({"lead_hours": L, **metrics(r.actual, r.fc, elig, s.mape_min_actual_mw)})
    pubs = []
    mm = m[m.actual.notna()].copy()
    mm["err"] = mm.fc - mm.actual
    mm["lead"] = (mm.start - mm.publish).dt.total_seconds() / 3600
    mm["pre"] = mm.publish <= mm.cutoff
    for p, x in mm.groupby("publish"):
        if len(x) < 6:
            continue  # skip tiny partial vintages for readability
        pubs.append({"publish_utc": _ts(p), "n": int(len(x)), "mae": _r(x.err.abs().mean()),
                     "bias": _r(x.err.mean()), "mean_lead_hours": _r(x.lead.mean()),
                     "share_before_cutoff_pct": _r(100 * x.pre.mean())})
    return {"cutoff_local": cutoff, "by_lead_time": by_lead, "by_publication": pubs}
