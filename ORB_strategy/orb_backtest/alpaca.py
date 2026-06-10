from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd


ALPACA_BARS_URL = "https://data.alpaca.markets/v2/stocks/bars"


class AlpacaDataError(RuntimeError):
    pass


class AlpacaRateLimitError(AlpacaDataError):
    pass


@dataclass(frozen=True)
class AlpacaCredentials:
    key_id: str
    secret_key: str

    @classmethod
    def from_env(cls) -> "AlpacaCredentials":
        key_id = os.environ.get("APCA_API_KEY_ID")
        secret_key = os.environ.get("APCA_API_SECRET_KEY")
        if not key_id or not secret_key:
            raise AlpacaDataError(
                "Missing Alpaca credentials. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY "
                "in the process environment, then rerun the backtest."
            )
        return cls(key_id=key_id, secret_key=secret_key)

    def headers(self) -> dict[str, str]:
        return {"APCA-API-KEY-ID": self.key_id, "APCA-API-SECRET-KEY": self.secret_key}


def fetch_stock_bars(
    symbol: str,
    timeframe: str,
    start_date: str | date,
    end_date: str | date,
    *,
    adjustment: str,
    credentials: AlpacaCredentials,
    feed: str = "sip",
    session=None,
    max_retries: int = 5,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict]:
    requests_session = session or _requests_session()
    params = {
        "symbols": symbol,
        "timeframe": timeframe,
        "start": _start_iso(start_date),
        "end": _end_iso(end_date),
        "limit": 10000,
        "adjustment": adjustment,
        "feed": feed,
    }
    bars: list[dict] = []

    while True:
        response = _get_with_retries(
            requests_session,
            ALPACA_BARS_URL,
            credentials.headers(),
            params,
            max_retries=max_retries,
            sleep=sleep,
        )
        payload = response.json()
        symbol_bars = payload.get("bars", {}).get(symbol, [])
        bars.extend(symbol_bars)
        next_page_token = payload.get("next_page_token")
        if not next_page_token:
            break
        params["page_token"] = next_page_token

    return bars


def download_alpaca_csvs(
    symbol: str,
    start_date: str | date,
    end_date: str | date,
    output_dir: str | Path,
    *,
    credentials: AlpacaCredentials | None = None,
    session=None,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[Path, Path]:
    creds = credentials or AlpacaCredentials.from_env()
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    intraday_rows = fetch_stock_bars(
        symbol,
        "1Min",
        start_date,
        end_date,
        adjustment="raw",
        credentials=creds,
        session=session,
        sleep=sleep,
    )
    daily_rows = fetch_stock_bars(
        symbol,
        "1Day",
        start_date,
        end_date,
        adjustment="all",
        credentials=creds,
        session=session,
        sleep=sleep,
    )

    intraday_path = out_dir / f"{symbol}_intraday.csv"
    daily_path = out_dir / f"{symbol}_daily.csv"
    normalize_intraday_bars(intraday_rows).to_csv(intraday_path, index=False)
    normalize_daily_bars(daily_rows).to_csv(daily_path, index=False)
    return intraday_path, daily_path


def normalize_intraday_bars(rows: Iterable[dict]) -> pd.DataFrame:
    df = _bars_frame(rows)
    if df.empty:
        return pd.DataFrame(columns=["datetime_et", "open", "high", "low", "close", "volume"])
    df["datetime_et"] = pd.to_datetime(df["t"], utc=True).dt.tz_convert("America/New_York")
    out = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    return out[["datetime_et", "open", "high", "low", "close", "volume"]].sort_values("datetime_et")


def normalize_daily_bars(rows: Iterable[dict]) -> pd.DataFrame:
    df = _bars_frame(rows)
    if df.empty:
        return pd.DataFrame(columns=["day", "open", "high", "low", "close"])
    df["day"] = pd.to_datetime(df["t"], utc=True).dt.tz_convert("America/New_York").dt.date
    out = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close"})
    return out[["day", "open", "high", "low", "close"]].sort_values("day").drop_duplicates("day")


def latest_complete_trading_day(now: pd.Timestamp | None = None) -> date:
    ts = now or pd.Timestamp.now(tz="America/New_York")
    if ts.tzinfo is None:
        ts = ts.tz_localize("America/New_York")
    else:
        ts = ts.tz_convert("America/New_York")

    candidate = ts.date()
    market_close_buffer = ts.replace(hour=16, minute=15, second=0, microsecond=0)
    if ts < market_close_buffer:
        candidate = candidate - timedelta(days=1)
    return _previous_trading_day(candidate)


def resolve_end_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    if str(value).strip().lower() in {"latest", "latest_complete", "current"}:
        return latest_complete_trading_day()
    return pd.Timestamp(value).date()


def _get_with_retries(session, url: str, headers: dict[str, str], params: dict, *, max_retries: int, sleep):
    for attempt in range(max_retries):
        response = session.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 429:
            wait = float(response.headers.get("Retry-After", 2**attempt))
            if attempt == max_retries - 1:
                raise AlpacaRateLimitError("Alpaca API rate limit persisted after retries.")
            sleep(wait)
            continue
        if response.status_code != 200:
            raise AlpacaDataError(f"Alpaca API error {response.status_code}: {response.text}")
        return response
    raise AlpacaRateLimitError("Alpaca API rate limit persisted after retries.")


def _bars_frame(rows: Iterable[dict]) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


def _requests_session():
    try:
        import requests
    except ModuleNotFoundError as exc:
        raise AlpacaDataError("Install requests to download Alpaca data: python -m pip install requests") from exc
    return requests.Session()


def _start_iso(value: str | date) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%dT00:00:00Z")


def _end_iso(value: str | date) -> str:
    end = pd.Timestamp(value) + pd.Timedelta(days=1)
    return end.strftime("%Y-%m-%dT00:00:00Z")


def _previous_trading_day(candidate: date) -> date:
    try:
        import exchange_calendars as xcals
    except ModuleNotFoundError:
        while candidate.weekday() >= 5:
            candidate = candidate - timedelta(days=1)
        return candidate

    cal = xcals.get_calendar("XNYS")
    start = (pd.Timestamp(candidate) - pd.Timedelta(days=14)).strftime("%Y-%m-%d")
    end = pd.Timestamp(candidate).strftime("%Y-%m-%d")
    sessions = cal.sessions_in_range(start, end)
    eligible = [session.date() for session in sessions if session.date() <= candidate]
    if not eligible:
        raise AlpacaDataError(f"No NYSE session found on or before {candidate}.")
    return eligible[-1]
