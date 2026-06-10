from __future__ import annotations

import pandas as pd

from orb_backtest.calendar import filter_regular_session_bars


def test_filter_regular_session_bars_removes_premarket_and_close_bar():
    bars = pd.DataFrame(
        {
            "datetime_et": [
                pd.Timestamp("2024-01-02 04:00", tz="America/New_York"),
                pd.Timestamp("2024-01-02 09:29", tz="America/New_York"),
                pd.Timestamp("2024-01-02 09:30", tz="America/New_York"),
                pd.Timestamp("2024-01-02 15:59", tz="America/New_York"),
                pd.Timestamp("2024-01-02 16:00", tz="America/New_York"),
            ],
            "open": [1, 2, 3, 4, 5],
            "high": [1, 2, 3, 4, 5],
            "low": [1, 2, 3, 4, 5],
            "close": [1, 2, 3, 4, 5],
        }
    )

    filtered = filter_regular_session_bars(bars)

    assert filtered["datetime_et"].dt.strftime("%H:%M").tolist() == ["09:30", "15:59"]
