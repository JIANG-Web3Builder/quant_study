import math

import pandas as pd

from orb_backtest.indicators import compute_atr_pct_lookup
from orb_backtest.metrics import monthly_return_table, summarize_performance


def test_compute_atr_pct_lookup_lags_by_one_trading_day():
    daily = pd.DataFrame(
        {
            "day": pd.date_range("2024-01-01", periods=4, freq="D"),
            "open": [100.0, 100.0, 100.0, 100.0],
            "high": [110.0, 112.0, 114.0, 116.0],
            "low": [90.0, 88.0, 86.0, 84.0],
            "close": [100.0, 101.0, 102.0, 103.0],
        }
    )

    lookup = compute_atr_pct_lookup(daily, period=2)

    assert math.isnan(lookup[pd.Timestamp("2024-01-01").date()])
    assert math.isnan(lookup[pd.Timestamp("2024-01-02").date()])
    assert lookup[pd.Timestamp("2024-01-03").date()] == 0.22
    assert lookup[pd.Timestamp("2024-01-04").date()] == 0.26


def test_performance_summary_and_monthly_returns_use_daily_aum():
    equity = pd.DataFrame(
        {
            "day": pd.to_datetime(["2024-01-02", "2024-01-31", "2024-02-01"]),
            "aum": [100.0, 110.0, 99.0],
        }
    )

    summary = summarize_performance(equity, initial_capital=100.0)
    monthly = monthly_return_table(equity, initial_capital=100.0)

    assert summary.loc["Total Return (%)", "Value"] == "-1.00"
    assert summary.loc["Max Drawdown (%)", "Value"] == "-10.00"
    assert monthly.loc[2024, "Jan"] == "10.00%"
    assert monthly.loc[2024, "Feb"] == "-10.00%"
    assert monthly.loc[2024, "Year Total"] == "-1.00%"
