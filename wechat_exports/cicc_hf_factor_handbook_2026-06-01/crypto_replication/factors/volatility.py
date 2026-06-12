"""Volatility factors (category: 波动率).

Direction note: per the handbook these are mostly "high volatility -> low future
return", i.e. negative-direction factors. Direction handling is applied in the
report layer, not here; these functions return the raw daily values.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import daily_apply, minute_returns


def _vol_return1min(g: pd.DataFrame) -> float:
    ret = minute_returns(g)
    if len(ret) < 2:
        return np.nan
    return float(np.std(ret, ddof=1))


def compute_vol_return1min(df_1m: pd.DataFrame) -> pd.Series:
    """Std of intraday minute returns (classic volatility benchmark)."""
    return daily_apply(df_1m, _vol_return1min)


def _vol_upVol(g: pd.DataFrame) -> float:
    ret = minute_returns(g)
    up = ret[ret > 0]
    if len(up) < 2:
        return np.nan
    return float(np.std(up, ddof=1))


def compute_vol_upVol(df_1m: pd.DataFrame) -> pd.Series:
    """Up-side volatility (top priority): std of positive minute returns."""
    return daily_apply(df_1m, _vol_upVol)


def _vol_downVol(g: pd.DataFrame) -> float:
    ret = minute_returns(g)
    down = ret[ret < 0]
    if len(down) < 2:
        return np.nan
    return float(np.std(down, ddof=1))


def compute_vol_downVol(df_1m: pd.DataFrame) -> pd.Series:
    """Down-side volatility: std of negative minute returns."""
    return daily_apply(df_1m, _vol_downVol)


def _vol_upRatio(g: pd.DataFrame) -> float:
    base = _vol_return1min(g)
    if not base or np.isnan(base) or base == 0:
        return np.nan
    return _vol_upVol(g) / base


def compute_vol_upRatio(df_1m: pd.DataFrame) -> pd.Series:
    """vol_upVol / vol_return1min."""
    return daily_apply(df_1m, _vol_upRatio)


def _vol_downRatio(g: pd.DataFrame) -> float:
    base = _vol_return1min(g)
    if not base or np.isnan(base) or base == 0:
        return np.nan
    return _vol_downVol(g) / base


def compute_vol_downRatio(df_1m: pd.DataFrame) -> pd.Series:
    """vol_downVol / vol_return1min."""
    return daily_apply(df_1m, _vol_downRatio)


def _vol_range1min(g: pd.DataFrame) -> float:
    ratio = (g["high"] / g["low"]).to_numpy(dtype="float64")
    ratio = ratio[np.isfinite(ratio)]
    if len(ratio) < 2:
        return np.nan
    return float(np.std(ratio, ddof=1))


def compute_vol_range1min(df_1m: pd.DataFrame) -> pd.Series:
    """Intraday std of high/low ratio."""
    return daily_apply(df_1m, _vol_range1min)


def _vol_volume1min(g: pd.DataFrame) -> float:
    vol = g["volume"].to_numpy(dtype="float64")
    if len(vol) < 2:
        return np.nan
    return float(np.std(vol, ddof=1))


def compute_vol_volume1min(df_1m: pd.DataFrame) -> pd.Series:
    """Intraday std of minute volume."""
    return daily_apply(df_1m, _vol_volume1min)


FACTORS = {
    "vol_return1min": compute_vol_return1min,
    "vol_upVol": compute_vol_upVol,
    "vol_downVol": compute_vol_downVol,
    "vol_upRatio": compute_vol_upRatio,
    "vol_downRatio": compute_vol_downRatio,
    "vol_range1min": compute_vol_range1min,
    "vol_volume1min": compute_vol_volume1min,
}
