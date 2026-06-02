from pathlib import Path

import pandas as pd
import pytest

from orb_backtest.data import load_daily_bars, load_intraday_bars


def test_load_intraday_accepts_caldt_and_filters_ticker(tmp_path: Path):
    path = tmp_path / "bars.csv"
    pd.DataFrame(
        {
            "ticker": ["TQQQ", "OTHER"],
            "caldt": ["2024-01-02 09:30:00-05:00", "2024-01-02 09:30:00-05:00"],
            "open": [100.0, 1.0],
            "high": [101.0, 1.0],
            "low": [99.0, 1.0],
            "close": [100.5, 1.0],
            "volume": [1000, 1],
        }
    ).to_csv(path, index=False)

    loaded = load_intraday_bars(path, ticker="TQQQ")

    assert list(loaded.columns) == ["datetime_et", "open", "high", "low", "close", "volume"]
    assert len(loaded) == 1
    assert str(loaded.iloc[0]["datetime_et"].tz) == "America/New_York"


def test_load_daily_requires_ohlc_columns(tmp_path: Path):
    path = tmp_path / "daily.csv"
    pd.DataFrame({"day": ["2024-01-02"], "open": [100.0]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="missing required columns"):
        load_daily_bars(path)


def test_load_intraday_treats_naive_datetime_et_as_new_york_time(tmp_path: Path):
    path = tmp_path / "bars.csv"
    pd.DataFrame(
        {
            "datetime_et": ["2024-01-02 09:30:00"],
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        }
    ).to_csv(path, index=False)

    loaded = load_intraday_bars(path, ticker="TQQQ")

    assert loaded.iloc[0]["datetime_et"].hour == 9
    assert loaded.iloc[0]["datetime_et"].minute == 30
