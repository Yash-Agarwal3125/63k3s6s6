"""Elexon BMRS client + record validation. Only WINDFOR and FUELHH(WIND) are used."""
import logging
import time
from datetime import date, datetime, timezone

import httpx

log = logging.getLogger("elexon")
logging.getLogger("httpx").setLevel(logging.WARNING)
TS_FMT = "%Y-%m-%dT%H:%M:%SZ"


def parse_ts(v) -> str | None:
    """Normalise a source timestamp to canonical UTC 'YYYY-MM-DDTHH:MM:SSZ'. Elexon timestamps are UTC ('Z')."""
    if not isinstance(v, str):
        return None
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:  # source documents UTC; treat naive as UTC and flag via caller if needed
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).strftime(TS_FMT)


def _num(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
        return None
    return float(v)


def parse_actuals(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep fuelType == WIND only. Returns (valid, rejected). Non-WIND rows are filtered, not 'rejected'."""
    ok, bad = [], []
    for r in rows:
        if r.get("fuelType") != "WIND":
            continue
        start, gen = parse_ts(r.get("startTime")), _num(r.get("generation"))
        if start is None or gen is None or gen < 0:
            bad.append({"reason": "invalid actual", "record": r})
            continue
        ok.append({
            "start": start, "generation": gen,
            "settlement_date": r.get("settlementDate"), "settlement_period": r.get("settlementPeriod"),
            "source_publish": parse_ts(r.get("publishTime")),
        })
    return ok, bad


def parse_forecasts(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    ok, bad = [], []
    for r in rows:
        start, pub, gen = parse_ts(r.get("startTime")), parse_ts(r.get("publishTime")), _num(r.get("generation"))
        if start is None or pub is None or gen is None or gen < 0:
            bad.append({"reason": "invalid forecast", "record": r})
            continue
        ok.append({"start": start, "publish": pub, "generation": gen})
    return ok, bad


class ElexonClient:
    def __init__(self, base_url: str, timeout: float = 30, transport=None, retries: int = 5):
        self.http = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)
        self.retries = retries

    def _get(self, path: str, params: dict) -> list[dict]:
        for attempt in range(self.retries):
            try:
                r = self.http.get(path, params=params)
                if r.status_code == 429 or r.status_code >= 500:
                    raise httpx.HTTPStatusError(f"{r.status_code}", request=r.request, response=r)
                r.raise_for_status()
                data = r.json()
                if not isinstance(data, list):
                    raise ValueError(f"unexpected payload type {type(data).__name__}")
                return data
            except (httpx.TransportError, httpx.HTTPStatusError, ValueError) as e:
                if attempt == self.retries - 1:
                    raise
                wait = min(2 ** attempt, 30)
                log.warning("retry %s %s after %ss: %s", path, params, wait, e)
                time.sleep(wait)
        return []

    def wind_actuals(self, d_from: date, d_to: date) -> list[dict]:
        return self._get("/datasets/FUELHH/stream", {
            "settlementDateFrom": d_from.isoformat(), "settlementDateTo": d_to.isoformat(), "fuelType": "WIND"})

    def wind_forecasts(self, pub_from: datetime, pub_to: datetime) -> list[dict]:
        return self._get("/datasets/WINDFOR/stream", {
            "publishDateTimeFrom": pub_from.strftime(TS_FMT), "publishDateTimeTo": pub_to.strftime(TS_FMT)})
