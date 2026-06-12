"""Information Coefficient (IC) analysis.

Computes per-period cross-sectional Spearman rank IC between a factor panel and
a forward-return panel, plus summary statistics (IC mean, ICIR, win rate).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


def select_rebalance_dates(index: pd.DatetimeIndex, freq: str) -> pd.DatetimeIndex:
    """Return the last available trading date of each week/month in ``index``.

    ``freq``: ``"weekly"`` or ``"monthly"``.
    """
    idx = pd.DatetimeIndex(index).sort_values()
    if freq == "weekly":
        rule = idx.to_period("W")
    elif freq == "monthly":
        rule = idx.to_period("M")
    else:
        raise ValueError(f"Unsupported freq: {freq!r}")
    s = pd.Series(idx, index=rule)
    last = s.groupby(level=0).last()
    return pd.DatetimeIndex(last.values)


def period_forward_returns(
    price_panel: pd.DataFrame, rebal_dates: pd.DatetimeIndex
) -> pd.DataFrame:
    """Forward returns over consecutive rebalance dates.

    ``price_panel``: index = date, columns = symbol, values = daily close.
    Row ``k`` holds the return from ``rebal_dates[k]`` to ``rebal_dates[k+1]``;
    the last row is NaN (no next period).
    """
    prices = price_panel.reindex(rebal_dates)
    fwd = prices.shift(-1) / prices - 1.0
    return fwd


@dataclass
class ICResult:
    ic_series: pd.Series
    ic_mean: float
    ic_std: float
    icir: float
    win_rate: float
    n_periods: int

    def as_dict(self) -> dict:
        return {
            "ic_mean": self.ic_mean,
            "ic_std": self.ic_std,
            "icir": self.icir,
            "win_rate": self.win_rate,
            "n_periods": self.n_periods,
        }


def _spearman(a: pd.Series, b: pd.Series) -> float:
    df = pd.concat([a, b], axis=1).dropna()
    if len(df) < 5:
        return np.nan
    if df.iloc[:, 0].nunique() < 2 or df.iloc[:, 1].nunique() < 2:
        return np.nan
    rho, _ = stats.spearmanr(df.iloc[:, 0], df.iloc[:, 1])
    return float(rho)


def compute_ic(factor_df: pd.DataFrame, forward_return_df: pd.DataFrame) -> ICResult:
    """Per-date cross-sectional Spearman IC and its summary statistics.

    Both inputs are wide (index = rebalance date, columns = symbol) and aligned.
    """
    common = factor_df.index.intersection(forward_return_df.index)
    ics = {}
    for date in common:
        ics[date] = _spearman(factor_df.loc[date], forward_return_df.loc[date])
    ic_series = pd.Series(ics, dtype="float64").sort_index().dropna()

    if ic_series.empty:
        return ICResult(ic_series, np.nan, np.nan, np.nan, np.nan, 0)

    ic_mean = float(ic_series.mean())
    ic_std = float(ic_series.std(ddof=1)) if len(ic_series) > 1 else np.nan
    icir = ic_mean / ic_std if ic_std and not np.isnan(ic_std) and ic_std != 0 else np.nan
    win_rate = float((ic_series > 0).mean())
    return ICResult(ic_series, ic_mean, ic_std, icir, win_rate, len(ic_series))
