"""Long-short quintile portfolio backtest.

Each rebalance period: go long the top 20% of symbols by (direction-adjusted)
factor value, short the bottom 20%, equal-weighted. The portfolio holds until
the next rebalance, earning the period forward return.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class LongShortResult:
    period_returns: pd.Series
    equity_curve: pd.Series
    ann_return: float
    sharpe: float
    max_drawdown: float
    n_periods: int

    def as_dict(self) -> dict:
        return {
            "ls_ann_return": self.ann_return,
            "ls_sharpe": self.sharpe,
            "ls_max_drawdown": self.max_drawdown,
            "ls_n_periods": self.n_periods,
        }


def _periods_per_year(freq: str) -> float:
    return {"weekly": 52.0, "monthly": 12.0}.get(freq, 252.0)


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return np.nan
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return float(drawdown.min())


def run_long_short(
    factor_df: pd.DataFrame,
    forward_return_df: pd.DataFrame,
    freq: str = "monthly",
    quantile: float = 0.2,
    direction: int = 1,
) -> LongShortResult:
    """Run the long-short backtest.

    ``factor_df`` / ``forward_return_df``: wide, aligned (index = rebalance date,
    columns = symbol). ``direction = -1`` reverses the factor sign.
    """
    common = factor_df.index.intersection(forward_return_df.index)
    period_returns = {}
    for date in common:
        f = (factor_df.loc[date] * direction).dropna()
        r = forward_return_df.loc[date]
        joined = pd.concat([f, r], axis=1, keys=["f", "r"]).dropna()
        n = len(joined)
        if n < 5:
            continue
        k = max(1, int(round(n * quantile)))
        ordered = joined.sort_values("f")
        short_leg = ordered.head(k)["r"].mean()
        long_leg = ordered.tail(k)["r"].mean()
        period_returns[date] = float(long_leg - short_leg)

    pr = pd.Series(period_returns, dtype="float64").sort_index()
    if pr.empty:
        empty = pd.Series(dtype="float64")
        return LongShortResult(empty, empty, np.nan, np.nan, np.nan, 0)

    equity = (1.0 + pr).cumprod()
    ppy = _periods_per_year(freq)
    mean_r = pr.mean()
    std_r = pr.std(ddof=1) if len(pr) > 1 else np.nan
    ann_return = float((1.0 + mean_r) ** ppy - 1.0)
    sharpe = (
        float(mean_r / std_r * np.sqrt(ppy))
        if std_r and not np.isnan(std_r) and std_r != 0
        else np.nan
    )
    return LongShortResult(pr, equity, ann_return, sharpe, _max_drawdown(equity), len(pr))
