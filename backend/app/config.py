"""Environment-driven settings."""
import os
from dataclasses import dataclass, field


def _list(name: str, default: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in os.getenv(name, default).split(",") if x.strip())


@dataclass(frozen=True)
class Settings:
    elexon_base_url: str = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")
    db_path: str = os.getenv("DB_PATH", "data/wind.sqlite")
    # Day-ahead decision cutoff: local Europe/London wall-clock time on D-1. ASSUMPTION (see docs).
    default_cutoff: str = os.getenv("DECISION_CUTOFF", "09:00")
    market_tz: str = os.getenv("MARKET_TZ", "Europe/London")
    window_start: str = os.getenv("WINDOW_START", "2026-01-01")
    window_end: str = os.getenv("WINDOW_END", "2026-01-31")
    forecast_lookback_days: int = int(os.getenv("FORECAST_LOOKBACK_DAYS", "4"))
    forecast_lookahead_days: int = int(os.getenv("FORECAST_LOOKAHEAD_DAYS", "4"))
    http_timeout_s: float = float(os.getenv("HTTP_TIMEOUT_S", "30"))
    # MAPE only where |actual| >= this (MW); below it the ratio is not meaningful.
    mape_min_actual_mw: float = float(os.getenv("MAPE_MIN_ACTUAL_MW", "100"))
    refresh_token: str = os.getenv("REFRESH_TOKEN", "")  # empty => refresh endpoint disabled
    auto_ingest_on_empty: bool = os.getenv("AUTO_INGEST_ON_EMPTY", "true").lower() == "true"
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: _list("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080")
    )


def get_settings() -> Settings:
    return Settings()
