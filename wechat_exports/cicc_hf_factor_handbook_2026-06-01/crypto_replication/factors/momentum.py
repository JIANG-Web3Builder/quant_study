"""Momentum / reversal factors (category: 动量反转).

Each ``compute_*`` function takes a single symbol's 1-minute DataFrame (with
columns ``open, high, low, close, volume, quote_volume`` and a DatetimeIndex or
``open_time`` column) and returns a daily-frequency ``pd.Series`` indexed by the
UTC date.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import daily_apply

OLS_WINDOW = 50


def _rolling_ols_beta_mean(g: pd.DataFrame, window: int = OLS_WINDOW) -> float:
    """Mean of rolling OLS betas of ``high ~ low`` over the day.

    For each rolling window of ``window`` bars:
        beta = cov(high_window, low_window) / var(low_window)
    The factor value is the mean of all betas in the day.
    """
    high = g["high"].to_numpy(dtype="float64")
    low = g["low"].to_numpy(dtype="float64")
    n = len(low)
    if n < window:
        return np.nan
    betas = []
    for i in range(window, n + 1):
        hw = high[i - window : i]
        lw = low[i - window : i]
        var = np.var(lw)
        if var == 0:
            continue
        cov = np.cov(hw, lw, bias=True)[0, 1]
        betas.append(cov / var)
    if not betas:
        return np.nan
    return float(np.mean(betas))


def compute_mmt_ols_beta_mean(df_1m: pd.DataFrame) -> pd.Series:
    """QRS/OLS beta momentum (top priority): mean of rolling high~low betas."""
    return daily_apply(df_1m, _rolling_ols_beta_mean)


def _last30(g: pd.DataFrame) -> float:
    close = g["close"].to_numpy(dtype="float64")
    if len(close) < 31:
        return np.nan
    return close[-1] / close[-31] - 1.0


def compute_mmt_last30(df_1m: pd.DataFrame) -> pd.Series:
    """Cumulative return of the last 30 minute bars of the day."""
    return daily_apply(df_1m, _last30)


def _segment_return(g: pd.DataFrame, start: int, end: int) -> float:
    close = g["close"].to_numpy(dtype="float64")
    if len(close) <= end - 1 or start >= len(close):
        # fall back to using available range
        seg = close[start : min(end, len(close))]
    else:
        seg = close[start:end]
    if len(seg) < 2:
        return np.nan
    return seg[-1] / seg[0] - 1.0


def compute_mmt_am(df_1m: pd.DataFrame) -> pd.Series:
    """Cumulative return of the first 720 bars (UTC 00:00-11:59)."""
    return daily_apply(df_1m, lambda g: _segment_return(g, 0, 720))


def compute_mmt_pm(df_1m: pd.DataFrame) -> pd.Series:
    """Cumulative return of the last 720 bars (UTC 12:00-23:59)."""
    return daily_apply(df_1m, lambda g: _segment_return(g, 720, 1440))


def _top20_volume_ret(g: pd.DataFrame) -> float:
    ret = g["close"].pct_change().to_numpy(dtype="float64")
    vol = g["volume"].to_numpy(dtype="float64")
    n = len(g)
    if n < 21:
        return np.nan
    idx = np.argsort(vol)[-20:]
    return float(np.nansum(ret[idx]))


def compute_mmt_top20VolumeRet(df_1m: pd.DataFrame) -> pd.Series:
    """Sum of returns over the 20 highest-volume bars of the day."""
    return daily_apply(df_1m, _top20_volume_ret)


FACTORS = {
    "mmt_ols_beta_mean": compute_mmt_ols_beta_mean,
    "mmt_last30": compute_mmt_last30,
    "mmt_am": compute_mmt_am,
    "mmt_pm": compute_mmt_pm,
    "mmt_top20VolumeRet": compute_mmt_top20VolumeRet,
}
