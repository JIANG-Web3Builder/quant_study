from __future__ import annotations

import pandas as pd

from orb_backtest.config import OrbConfig
from orb_backtest.plots import _account_value_ticks, _format_account_value, _prepare_curve_for_plot


def test_account_value_ticks_start_from_initial_capital_and_double():
    ticks = _account_value_ticks(initial_capital=10_000, max_value=95_000)

    assert ticks == [10_000, 20_000, 40_000, 80_000, 160_000]


def test_format_account_value_uses_dollar_units():
    assert _format_account_value(10_000) == "$10k"
    assert _format_account_value(1_250_000) == "$1.25m"


def test_prepare_curve_for_plot_prepends_initial_capital():
    config = OrbConfig(start_date="2020-01-01", initial_capital=10_000)
    equity = pd.DataFrame({"day": ["2020-01-02"], "aum": [10_500]})

    curve = _prepare_curve_for_plot(equity, config)

    assert curve.iloc[0]["day"] == pd.Timestamp("2020-01-01")
    assert curve.iloc[0]["aum"] == 10_000
    assert curve.iloc[1]["aum"] == 10_500
