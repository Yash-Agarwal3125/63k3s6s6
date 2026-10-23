"""Unit + API tests. All data here is synthetic test fixture data; no network access."""
import httpx
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import analysis as A
from app import db, elexon, ingest, main
from app.config import Settings


# ---------- parsing ----------
def test_parse_actuals_filters_wind_and_rejects_bad():
    rows = [
        {"fuelType": "WIND", "startTime": "2026-01-01T00:00:00Z", "generation": 100, "settlementDate": "2026-01-01", "settlementPeriod": 1},
        {"fuelType": "CCGT", "startTime": "2026-01-01T00:00:00Z", "generation": 999},
        {"fuelType": "WIND", "startTime": "garbage", "generation": 5},
        {"fuelType": "WIND", "startTime": "2026-01-01T00:30:00Z", "generation": None},
        {"fuelType": "WIND", "startTime": "2026-01-01T01:00:00Z", "generation": -4},
    ]
    ok, bad = elexon.parse_actuals(rows)
    assert [r["generation"] for r in ok] == [100.0]
    assert len(bad) == 3  # non-WIND is filtered, not "rejected"


def test_parse_forecasts_normalises_offsets_to_utc():
    ok, bad = elexon.parse_forecasts([
        {"startTime": "2026-01-02T12:00:00+01:00", "publishTime": "2026-01-01T09:00:00Z", "generation": 10},
        {"startTime": "2026-01-02T12:00:00Z", "publishTime": None, "generation": 10}])
    assert ok[0]["start"] == "2026-01-02T11:00:00Z" and len(bad) == 1


# ---------- timezone / cutoff ----------
def test_cutoff_gmt_and_bst():
    s = pd.Series(pd.to_datetime(["2026-01-02 12:00", "2026-07-02 12:00"], utc=True))
    c = A.decision_cutoff_utc(s, "09:00", "Europe/London")
    assert c[0] == pd.Timestamp("2026-01-01 09:00", tz="UTC")  # GMT
    assert c[1] == pd.Timestamp("2026-07-01 08:00", tz="UTC")  # BST = UTC+1


def test_parse_cutoff_validation():
    assert A.parse_cutoff("09:30") == "09:30"
    for bad in ("9:00", "24:00", "09:60", "abc"):
        with pytest.raises(ValueError):
            A.parse_cutoff(bad)


# ---------- metrics ----------
def test_metrics_formulas_and_missing():
    act = pd.Series([100.0, 200.0, np.nan, 0.0, 400.0])
    fc = pd.Series([110.0, 180.0, 50.0, 20.0, np.nan])
    m = A.metrics(act, fc, eligible=5, mape_min=50)
    e = np.array([10, -20, 20.0])  # matched rows only: (100,110) (200,180) (0,20)
    assert m["n"] == 3 and m["coverage_pct"] == 60.0
    assert m["mae"] == round(np.abs(e).mean(), 2)
    assert m["rmse"] == round(np.sqrt((e**2).mean()), 2)
    assert m["bias"] == round(e.mean(), 2)  # positive = overforecast
    assert m["n_mape"] == 2  # zero actual excluded from MAPE
    assert m["mape_pct"] == round(100 * np.mean([10 / 100, 20 / 200]), 2)


def test_metrics_no_matches_returns_none_not_zero():
    m = A.metrics(pd.Series([np.nan]), pd.Series([1.0]), 1, 100)
    assert m["n"] == 0 and m["mae"] is None and m["coverage_pct"] == 0.0


# ---------- fixture DB: selection logic ----------
@pytest.fixture()
def settings(tmp_path):
    s = Settings(db_path=str(tmp_path / "t.sqlite"), refresh_token="")
    with db.connect(s.db_path) as con:
        act = []
        for d in ("2026-01-01", "2026-01-02"):
            for i in range(48):
                t = pd.Timestamp(d, tz="UTC") + pd.Timedelta(minutes=30 * i)
                if d == "2026-01-02" and t.hour == 13:
                    continue  # a missing actual
                act.append({"start": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "generation": 150.0 if (d, t.hour, t.minute) == ("2026-01-02", 12, 0) else 1000.0,
                            "settlement_date": d, "settlement_period": i + 1, "source_publish": None})
        db.upsert_actuals(con, act, "now")
        T = "2026-01-02T12:00:00Z"
        fc = [  # publish vintages around the 09:00 D-1 cutoff
            {"start": T, "publish": "2026-01-01T08:30:00Z", "generation": 100.0},
            {"start": T, "publish": "2026-01-01T09:00:00Z", "generation": 200.0},  # exactly at cutoff => eligible
            {"start": T, "publish": "2026-01-01T09:00:01Z", "generation": 300.0},  # 1s late => excluded
            {"start": T, "publish": "2026-01-02T11:00:00Z", "generation": 400.0},  # latest, post-cutoff
            {"start": "2026-01-02T13:00:00Z", "publish": "2026-01-01T08:00:00Z", "generation": 50.0},  # forecast, no actual
            {"start": "2026-01-02T14:00:00Z", "publish": "2026-01-01T10:00:00Z", "generation": 70.0},  # only post-cutoff
        ]
        db.upsert_forecasts(con, fc, "now")
        con.execute("INSERT INTO ingest_runs(started_at,finished_at,status,stats) VALUES('a','2026-01-03T00:00:00Z','success','{}')")
    return s


def test_selection_excludes_late_vintages(settings):
    g, _, _ = A.frame(settings, "09:00")
    r = g[g.start == pd.Timestamp("2026-01-02 12:00", tz="UTC")].iloc[0]
    assert r.dec_fc == 200.0 and r.lat_fc == 400.0
    assert r.dec_pub == pd.Timestamp("2026-01-01 09:00", tz="UTC") and r.status == "matched"
    assert r.lead_h == 27.0 and r.actual == 150.0


def test_missing_values_not_zero_filled(settings):
    g, _, _ = A.frame(settings, "09:00")
    def row(h):
        return g[g.start == pd.Timestamp(f"2026-01-02 {h}", tz="UTC")].iloc[0]

    assert row("13:00").status == "no_actual" and pd.isna(row("13:00").actual)
    assert row("14:00").status == "no_forecast_at_cutoff" and pd.isna(row("14:00").dec_fc)
    assert row("12:30").status == "no_half_hourly_forecast"
    m = A.series_metrics(g, "dec_fc", settings)
    assert m["n"] == 1 and m["eligible"] == 744 and m["bias"] == 50.0 and m["mae"] == 50.0


def test_cutoff_param_changes_selection(settings):
    g, _, _ = A.frame(settings, "08:45")
    r = g[g.start == pd.Timestamp("2026-01-02 12:00", tz="UTC")].iloc[0]
    assert r.dec_fc == 100.0


def test_january_boundary_grid(settings):
    g, _, _ = A.frame(settings, "09:00")
    assert len(g) == 31 * 48 and g.settlement_date.iloc[0] == "2026-01-01" and g.settlement_date.iloc[-1] == "2026-01-31"
    assert len(A.in_range(g, "2026-01-02", "2026-01-02")) == 48


# ---------- ingestion (mocked transport) ----------
def test_ingest_idempotent_dedupes_and_filters(tmp_path):
    wind = [{"fuelType": "WIND", "startTime": "2026-01-01T00:00:00Z", "generation": 5, "settlementDate": "2026-01-01", "settlementPeriod": 1},
            {"fuelType": "WIND", "startTime": "2025-12-31T23:30:00Z", "generation": 5}]  # outside window
    fcs = [{"startTime": "2026-01-01T10:00:00Z", "publishTime": "2025-12-31T07:30:00Z", "generation": 9},
           {"startTime": "2026-02-05T10:00:00Z", "publishTime": "2025-12-31T07:30:00Z", "generation": 9}]  # outside window

    def handler(req: httpx.Request):
        return httpx.Response(200, json=wind if "FUELHH" in req.url.path else fcs)

    s = Settings(db_path=str(tmp_path / "i.sqlite"), forecast_lookback_days=2, forecast_lookahead_days=2)
    c = elexon.ElexonClient("http://x", transport=httpx.MockTransport(handler))
    st1 = ingest.run_ingest(s, c)
    st2 = ingest.run_ingest(s, c)
    assert st1["actual_wind_rows_kept"] == 1 and st1["forecast_rows_kept"] == 1 and st1["forecast_duplicates_dropped"] > 0
    with db.connect(s.db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM actuals").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0] == 1
    assert st2["forecast_rows_kept"] == 1


def test_client_retries_then_raises():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(503)

    c = elexon.ElexonClient("http://x", transport=httpx.MockTransport(handler), retries=2)
    import app.elexon as e
    e.time.sleep = lambda *_: None
    with pytest.raises(httpx.HTTPStatusError):
        c.wind_actuals(pd.Timestamp("2026-01-01").date(), pd.Timestamp("2026-01-02").date())
    assert len(calls) == 2


# ---------- API ----------
@pytest.fixture()
def client(settings, monkeypatch):
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    return TestClient(main.app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["data_loaded"] is True


def test_summary_shape_and_values(client):
    r = client.get("/api/v1/summary?start=2026-01-02&end=2026-01-02")
    assert r.status_code == 200
    j = r.json()
    assert set(j) == {"meta", "data"} and j["meta"]["cutoff_local"] == "09:00"
    assert j["data"]["decision_forecast"]["bias"] == 50.0 and j["data"]["latest_forecast"]["bias"] == -340.0  # (400-150, 70-1000) / 2
    assert j["data"]["decision_forecast"]["eligible"] == 24


@pytest.mark.parametrize("q", ["start=2025-12-31", "end=2026-02-01", "start=2026-01-05&end=2026-01-04",
                               "cutoff=25:00", "start=notadate"])
def test_query_validation(client, q):
    r = client.get(f"/api/v1/summary?{q}")
    assert r.status_code == 422 and "error" in r.json()


def test_generation_and_errors_and_vintages(client):
    g = client.get("/api/v1/generation?start=2026-01-02&end=2026-01-02").json()["data"]
    assert len(g) == 48
    row = next(x for x in g if x["start_utc"] == "2026-01-02T12:00:00Z")
    assert row["decision_forecast_mw"] == 200 and row["latest_forecast_mw"] == 400 and row["latest_postdates_cutoff"]
    miss = next(x for x in g if x["start_utc"] == "2026-01-02T13:00:00Z")
    assert miss["actual_mw"] is None and miss["error_mw"] is None
    e = client.get("/api/v1/errors?forecast=latest&start=2026-01-02&end=2026-01-02").json()["data"]
    assert e["metrics"]["n"] == 2 and sum(b["count"] for b in e["histogram"]) == 2
    assert client.get("/api/v1/errors?forecast=bogus").status_code == 422
    v = client.get("/api/v1/forecast-vintages").json()["data"]
    assert [x["lead_hours"] for x in v["by_lead_time"]] == A.LEADS_H


def test_metadata(client):
    d = client.get("/api/v1/metadata").json()["data"]
    assert d["coverage"]["expected_half_hour_periods"] == 1488 and d["coverage"]["actual_periods_present"] == 94


def test_refresh_disabled_and_auth(client, settings, monkeypatch):
    assert client.post("/api/v1/refresh").status_code == 403
    monkeypatch.setattr(main, "get_settings", lambda: Settings(db_path=settings.db_path, refresh_token="secret"))
    assert client.post("/api/v1/refresh", headers={"x-refresh-token": "nope"}).status_code == 401


def test_no_data_returns_503(tmp_path, monkeypatch):
    s = Settings(db_path=str(tmp_path / "empty.sqlite"))
    monkeypatch.setattr(main, "get_settings", lambda: s)
    assert TestClient(main.app).get("/api/v1/summary").status_code == 503
