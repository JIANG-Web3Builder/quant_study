from datetime import date

import pandas as pd

from orb_backtest.config import OrbConfig
from orb_backtest.engine import run_orb_backtest


def make_minutes(day: str, rows: list[tuple[str, float, float, float, float]]) -> pd.DataFrame:
    records = []
    for clock, open_, high, low, close in rows:
        records.append(
            {
                "datetime_et": pd.Timestamp(f"{day} {clock}", tz="America/New_York"),
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000,
            }
        )
    return pd.DataFrame(records)


def base_config(**overrides) -> OrbConfig:
    values = {
        "ticker": "TQQQ",
        "start_date": "2024-01-02",
        "end_date": "2024-01-04",
        "orb_minutes": 5,
        "risk": 0.01,
        "max_leverage": 4.0,
        "initial_capital": 25_000.0,
        "commission": 0.0005,
        "atr_period": 14,
        "stop_atr": 0.05,
    }
    values.update(overrides)
    return OrbConfig(**values)


def test_hl_long_uses_nth_bar_direction_and_enters_next_open():
    intraday = make_minutes(
        "2024-01-02",
        [
            ("09:30", 100.0, 101.0, 99.0, 100.5),
            ("09:31", 101.0, 102.0, 100.0, 101.5),
            ("09:32", 102.0, 103.0, 101.0, 102.5),
            ("09:33", 103.0, 104.0, 102.0, 103.5),
            ("09:34", 104.0, 105.0, 103.0, 104.5),
            ("09:35", 106.0, 108.0, 104.0, 107.0),
            ("09:36", 107.0, 109.0, 106.0, 108.0),
        ],
    )

    result = run_orb_backtest(intraday, base_config(), stop_type="HL")

    assert len(result) == 1
    row = result.iloc[0]
    assert row["day"] == date(2024, 1, 2)
    assert row["side"] == 1
    assert row["entry"] == 106.0
    assert row["stop_price"] == 99.0
    assert row["shares"] == 35
    assert row["exit_reason"] == "close"
    assert row["gross_pnl"] == 70.0
    assert row["fees"] == 3.745
    assert row["pnl"] == 66.255


def test_hl_short_uses_opening_range_high_as_stop():
    intraday = make_minutes(
        "2024-01-02",
        [
            ("09:30", 100.0, 101.0, 99.0, 99.5),
            ("09:31", 99.0, 100.0, 98.0, 98.5),
            ("09:32", 98.0, 99.0, 97.0, 97.5),
            ("09:33", 97.0, 98.0, 96.0, 96.5),
            ("09:34", 96.0, 97.0, 95.0, 95.5),
            ("09:35", 94.0, 95.0, 90.0, 91.0),
        ],
    )

    result = run_orb_backtest(intraday, base_config(), stop_type="HL")

    row = result.iloc[0]
    assert row["side"] == -1
    assert row["entry"] == 94.0
    assert row["stop_price"] == 101.0
    assert row["exit_reason"] == "close"
    assert row["gross_pnl"] == 105.0
    assert row["fees"] == 3.2375
    assert row["pnl"] == 101.7625


def test_atr_stop_skips_day_when_lookup_missing():
    intraday = make_minutes(
        "2024-01-02",
        [
            ("09:30", 100.0, 101.0, 99.0, 100.5),
            ("09:31", 101.0, 102.0, 100.0, 101.5),
            ("09:32", 102.0, 103.0, 101.0, 102.5),
            ("09:33", 103.0, 104.0, 102.0, 103.5),
            ("09:34", 104.0, 105.0, 103.0, 104.5),
            ("09:35", 106.0, 108.0, 104.0, 107.0),
        ],
    )

    result = run_orb_backtest(intraday, base_config(), stop_type="ATR", atr_lookup={})

    assert result.empty


def test_position_size_is_capped_by_max_leverage():
    intraday = make_minutes(
        "2024-01-02",
        [
            ("09:30", 100.0, 100.2, 99.9, 100.1),
            ("09:31", 100.1, 100.3, 100.0, 100.2),
            ("09:32", 100.2, 100.4, 100.1, 100.3),
            ("09:33", 100.3, 100.5, 100.2, 100.4),
            ("09:34", 100.4, 100.6, 100.3, 100.5),
            ("09:35", 100.0, 101.0, 99.8, 100.5),
        ],
    )

    result = run_orb_backtest(
        intraday,
        base_config(max_leverage=1.0),
        stop_type="ATR",
        atr_lookup={date(2024, 1, 2): 0.001},
    )

    assert result.iloc[0]["shares"] == 250
