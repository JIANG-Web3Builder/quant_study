"""Higher-moment shape factors (category: 高阶特征)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .base import daily_apply, minute_returns


def _vol_share(g: pd.DataFrame) -> np.ndarray:
    vol = g["volume"].to_numpy(dtype="float64")
    total = vol.sum()
    if total == 0:
        return np.array([])
    return vol / total


def _skew(g: pd.DataFrame) -> float:
    ret = minute_returns(g)
    if len(ret) < 3:
        return np.nan
    return float(stats.skew(ret, bias=False, nan_policy="omit"))


def compute_shape_skew(df_1m: pd.DataFrame) -> pd.Series:
    """Skewness of minute returns (top priority)."""
    return daily_apply(df_1m, _skew)


def _kurt(g: pd.DataFrame) -> float:
    ret = minute_returns(g)
    if len(ret) < 4:
        return np.nan
    return float(stats.kurtosis(ret, bias=False, nan_policy="omit"))


def compute_shape_kurt(df_1m: pd.DataFrame) -> pd.Series:
    """Excess kurtosis of minute returns."""
    return daily_apply(df_1m, _kurt)


def _skratio(g: pd.DataFrame) -> float:
    k = _kurt(g)
    if k is None or np.isnan(k) or k == 0:
        return np.nan
    return _skew(g) / k


def compute_shape_skratio(df_1m: pd.DataFrame) -> pd.Series:
    """skew / kurt (NaN when kurt == 0)."""
    return daily_apply(df_1m, _skratio)


def _skewVol(g: pd.DataFrame) -> float:
    share = _vol_share(g)
    if len(share) < 3:
        return np.nan
    return float(stats.skew(share, bias=False))


def compute_shape_skewVol(df_1m: pd.DataFrame) -> pd.Series:
    """Skewness of the minute volume-share series."""
    return daily_apply(df_1m, _skewVol)


def _kurtVol(g: pd.DataFrame) -> float:
    share = _vol_share(g)
    if len(share) < 4:
        return np.nan
    return float(stats.kurtosis(share, bias=False))


def compute_shape_kurtVol(df_1m: pd.DataFrame) -> pd.Series:
    """Kurtosis of the minute volume-share series."""
    return daily_apply(df_1m, _kurtVol)


def _skratioVol(g: pd.DataFrame) -> float:
    k = _kurtVol(g)
    if k is None or np.isnan(k) or k == 0:
        return np.nan
    return _skewVol(g) / k


def compute_shape_skratioVol(df_1m: pd.DataFrame) -> pd.Series:
    """shape_skewVol / shape_kurtVol."""
    return daily_apply(df_1m, _skratioVol)


FACTORS = {
    "shape_skew": compute_shape_skew,
    "shape_kurt": compute_shape_kurt,
    "shape_skratio": compute_shape_skratio,
    "shape_skewVol": compute_shape_skewVol,
    "shape_kurtVol": compute_shape_kurtVol,
    "shape_skratioVol": compute_shape_skratioVol,
}
