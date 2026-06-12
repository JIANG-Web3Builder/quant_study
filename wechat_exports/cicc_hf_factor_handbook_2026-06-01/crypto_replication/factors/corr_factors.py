"""Price-volume correlation factors (category: 量价相关性)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import daily_apply


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3 or len(b) < 3 or len(a) != len(b):
        return np.nan
    mask = np.isfinite(a) & np.isfinite(b)
    a, b = a[mask], b[mask]
    if len(a) < 3:
        return np.nan
    if np.std(a) == 0 or np.std(b) == 0:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def _close_vol(g: pd.DataFrame):
    return (
        g["close"].to_numpy(dtype="float64"),
        g["volume"].to_numpy(dtype="float64"),
    )


def compute_corr_pv(df_1m: pd.DataFrame) -> pd.Series:
    """corr(close, volume) (top priority)."""

    def f(g):
        c, v = _close_vol(g)
        return _safe_corr(c, v)

    return daily_apply(df_1m, f)


def compute_corr_pvl(df_1m: pd.DataFrame) -> pd.Series:
    """corr(close[1:], volume[:-1]) -- close vs volume leading by 1 (top)."""

    def f(g):
        c, v = _close_vol(g)
        return _safe_corr(c[1:], v[:-1])

    return daily_apply(df_1m, f)


def compute_corr_pvd(df_1m: pd.DataFrame) -> pd.Series:
    """corr(close[:-1], volume[1:]) -- close vs volume lagging by 1."""

    def f(g):
        c, v = _close_vol(g)
        return _safe_corr(c[:-1], v[1:])

    return daily_apply(df_1m, f)


def compute_corr_prv(df_1m: pd.DataFrame) -> pd.Series:
    """corr(returns, volume)."""

    def f(g):
        r = g["close"].pct_change().to_numpy(dtype="float64")[1:]
        v = g["volume"].to_numpy(dtype="float64")[1:]
        return _safe_corr(r, v)

    return daily_apply(df_1m, f)


def compute_corr_prvr(df_1m: pd.DataFrame) -> pd.Series:
    """corr(returns, volume_change_rate)."""

    def f(g):
        r = g["close"].pct_change().to_numpy(dtype="float64")
        vcr = g["volume"].pct_change().to_numpy(dtype="float64")
        r, vcr = r[1:], vcr[1:]
        return _safe_corr(r, vcr)

    return daily_apply(df_1m, f)


def compute_corr_pvr(df_1m: pd.DataFrame) -> pd.Series:
    """corr(close, volume_change_rate)."""

    def f(g):
        c = g["close"].to_numpy(dtype="float64")[1:]
        vcr = g["volume"].pct_change().to_numpy(dtype="float64")[1:]
        return _safe_corr(c, vcr)

    return daily_apply(df_1m, f)


FACTORS = {
    "corr_pv": compute_corr_pv,
    "corr_pvl": compute_corr_pvl,
    "corr_pvd": compute_corr_pvd,
    "corr_prv": compute_corr_prv,
    "corr_prvr": compute_corr_prvr,
    "corr_pvr": compute_corr_pvr,
}
