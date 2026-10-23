"""SQLite persistence (WAL, upserts, indexes)."""
import json
import os
import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS actuals(
  start_utc TEXT PRIMARY KEY, generation_mw REAL NOT NULL, settlement_date TEXT, settlement_period INTEGER,
  source_publish_utc TEXT, source TEXT NOT NULL DEFAULT 'FUELHH', ingested_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS forecasts(
  start_utc TEXT NOT NULL, publish_utc TEXT NOT NULL, generation_mw REAL NOT NULL,
  source TEXT NOT NULL DEFAULT 'WINDFOR', ingested_at TEXT NOT NULL, PRIMARY KEY(start_utc, publish_utc));
CREATE INDEX IF NOT EXISTS ix_fc_publish ON forecasts(publish_utc);
CREATE TABLE IF NOT EXISTS ingest_runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, finished_at TEXT, status TEXT, stats TEXT, error TEXT);
"""


@contextmanager
def connect(path: str):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def upsert_actuals(con, rows, ts):
    con.executemany(
        "INSERT OR REPLACE INTO actuals(start_utc,generation_mw,settlement_date,settlement_period,source_publish_utc,ingested_at)"
        " VALUES(?,?,?,?,?,?)",
        [(r["start"], r["generation"], r["settlement_date"], r["settlement_period"], r["source_publish"], ts) for r in rows])


def upsert_forecasts(con, rows, ts):
    con.executemany(
        "INSERT OR REPLACE INTO forecasts(start_utc,publish_utc,generation_mw,ingested_at) VALUES(?,?,?,?)",
        [(r["start"], r["publish"], r["generation"], ts) for r in rows])


def last_success(con) -> dict | None:
    r = con.execute("SELECT * FROM ingest_runs WHERE status='success' ORDER BY id DESC LIMIT 1").fetchone()
    if not r:
        return None
    d = dict(r)
    d["stats"] = json.loads(d["stats"] or "{}")
    return d
