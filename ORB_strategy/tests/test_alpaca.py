from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from orb_backtest.alpaca import (
    AlpacaCredentials,
    AlpacaDataError,
    AlpacaRateLimitError,
    download_alpaca_csvs,
    fetch_stock_bars,
    latest_complete_trading_day,
    normalize_daily_bars,
    normalize_intraday_bars,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: dict, headers: dict[str, str] | None = None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = responses
        self.calls: list[dict] = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "params": dict(params), "timeout": timeout})
        return self.responses.pop(0)


def test_fetch_stock_bars_paginates_and_sets_alpaca_params():
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "bars": {"TQQQ": [{"t": "2024-01-02T14:30:00Z", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10}]},
                    "next_page_token": "next",
                },
            ),
            FakeResponse(
                200,
                {
                    "bars": {"TQQQ": [{"t": "2024-01-02T14:31:00Z", "o": 2, "h": 3, "l": 1.5, "c": 2.5, "v": 11}]},
                },
            ),
        ]
    )

    bars = fetch_stock_bars(
        "TQQQ",
        "1Min",
        "2024-01-02",
        "2024-01-03",
        adjustment="raw",
        credentials=AlpacaCredentials("key", "secret"),
        session=session,
        sleep=lambda _seconds: None,
    )

    assert len(bars) == 2
    assert session.calls[0]["params"]["feed"] == "sip"
    assert session.calls[0]["params"]["adjustment"] == "raw"
    assert session.calls[1]["params"]["page_token"] == "next"
    assert session.calls[0]["headers"]["APCA-API-KEY-ID"] == "key"


def test_fetch_stock_bars_raises_rate_limit_after_retries():
    session = FakeSession([FakeResponse(429, {}, {"Retry-After": "0"}) for _ in range(3)])

    with pytest.raises(AlpacaRateLimitError):
        fetch_stock_bars(
            "TQQQ",
            "1Min",
            "2024-01-02",
            "2024-01-03",
            adjustment="raw",
            credentials=AlpacaCredentials("key", "secret"),
            session=session,
            max_retries=3,
            sleep=lambda _seconds: None,
        )

    assert len(session.calls) == 3


def test_normalize_intraday_bars_matches_loader_shape():
    rows = [
        {"t": "2024-01-02T14:30:00Z", "o": 100, "h": 101, "l": 99, "c": 100.5, "v": 1000},
        {"t": "2024-01-02T14:31:00Z", "o": 101, "h": 102, "l": 100, "c": 101.5, "v": 2000},
    ]

    df = normalize_intraday_bars(rows)

    assert list(df.columns) == ["datetime_et", "open", "high", "low", "close", "volume"]
    assert str(df.iloc[0]["datetime_et"].tz) == "America/New_York"
    assert df.iloc[0]["datetime_et"].hour == 9


def test_normalize_daily_bars_matches_loader_shape():
    rows = [{"t": "2024-01-02T05:00:00Z", "o": 100, "h": 101, "l": 99, "c": 100.5, "v": 1000}]

    df = normalize_daily_bars(rows)

    assert list(df.columns) == ["day", "open", "high", "low", "close"]
    assert df.iloc[0]["day"] == pd.Timestamp("2024-01-02").date()


def test_download_alpaca_csvs_writes_intraday_and_daily(tmp_path: Path):
    session = FakeSession(
        [
            FakeResponse(200, {"bars": {"TQQQ": [{"t": "2024-01-02T14:30:00Z", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10}]}}),
            FakeResponse(200, {"bars": {"TQQQ": [{"t": "2024-01-02T05:00:00Z", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10}]}}),
        ]
    )

    intraday_path, daily_path = download_alpaca_csvs(
        "TQQQ",
        "2024-01-02",
        "2024-01-03",
        tmp_path,
        credentials=AlpacaCredentials("key", "secret"),
        session=session,
        sleep=lambda _seconds: None,
    )

    assert intraday_path == tmp_path / "TQQQ_intraday.csv"
    assert daily_path == tmp_path / "TQQQ_daily.csv"
    assert pd.read_csv(intraday_path).columns.tolist() == ["datetime_et", "open", "high", "low", "close", "volume"]
    assert session.calls[0]["params"]["timeframe"] == "1Min"
    assert session.calls[0]["params"]["adjustment"] == "raw"
    assert session.calls[1]["params"]["timeframe"] == "1Day"
    assert session.calls[1]["params"]["adjustment"] == "all"


def test_latest_complete_trading_day_uses_previous_day_before_market_close():
    now = pd.Timestamp("2026-06-10 10:00:00", tz="America/New_York")

    assert latest_complete_trading_day(now) == pd.Timestamp("2026-06-09").date()


def test_missing_credentials_are_actionable(monkeypatch):
    monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)

    with pytest.raises(AlpacaDataError, match="APCA_API_KEY_ID"):
        AlpacaCredentials.from_env()
