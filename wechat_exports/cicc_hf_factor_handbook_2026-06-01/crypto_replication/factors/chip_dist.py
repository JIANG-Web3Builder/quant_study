"""Chip-distribution factors (category: 筹码分布).

Build a volume-weighted distribution of intraday minute returns over 100
equal-width bins, then derive quantile / shape statistics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import daily_apply

N_BINS = 100


def _binned(g: pd.DataFrame):
    """Return (bin_centers, bin_volume) for the day's return distribution."""
    ret = g["close"].pct_change().to_numpy(dtype="float64")
    vol = g["volume"].to_numpy(dtype="float64")
    ret, vol = ret[1:], vol[1:]
    mask = np.isfinite(ret) & np.isfinite(vol)
    ret, vol = ret[mask], vol[mask]
    if len(ret) < 10 or ret.min() == ret.max():
        return None, None
    edges = np.linspace(ret.min(), ret.max(), N_BINS + 1)
    centers = (edges[:-1] + edges[1:]) / 2.0
    idx = np.clip(np.digitize(ret, edges) - 1, 0, N_BINS - 1)
    bin_vol = np.zeros(N_BINS, dtype="float64")
    np.add.at(bin_vol, idx, vol)
    return centers, bin_vol


def _cdf_quantile(centers, bin_vol, q: float) -> float:
    total = bin_vol.sum()
    if total == 0:
        return np.nan
    cdf = np.cumsum(bin_vol) / total
    i = int(np.searchsorted(cdf, q, side="left"))
    i = min(i, len(centers) - 1)
    return float(centers[i])


def compute_doc_vol_pdf90(df_1m: pd.DataFrame) -> pd.Series:
    """Return quantile where the volume-weighted CDF reaches 90% (top)."""

    def f(g):
        c, v = _binned(g)
        if c is None:
            return np.nan
        return _cdf_quantile(c, v, 0.90)

    return daily_apply(df_1m, f)


def compute_doc_vol_pdf95(df_1m: pd.DataFrame) -> pd.Series:
    """Return quantile where the volume-weighted CDF reaches 95% (top)."""

    def f(g):
        c, v = _binned(g)
        if c is None:
            return np.nan
        return _cdf_quantile(c, v, 0.95)

    return daily_apply(df_1m, f)


def compute_doc_vol_pdf90bi(df_1m: pd.DataFrame) -> pd.Series:
    """Two-sided 90%: (pdf90 - pdf10) / 2 (width of central 80% volume)."""

    def f(g):
        c, v = _binned(g)
        if c is None:
            return np.nan
        return (_cdf_quantile(c, v, 0.90) - _cdf_quantile(c, v, 0.10)) / 2.0

    return daily_apply(df_1m, f)


def _weighted_moments(centers, bin_vol):
    total = bin_vol.sum()
    if total == 0:
        return None
    w = bin_vol / total
    mean = np.average(centers, weights=w)
    var = np.average((centers - mean) ** 2, weights=w)
    return mean, var, w


def compute_doc_skew(df_1m: pd.DataFrame) -> pd.Series:
    """Skewness of the volume-weighted return distribution."""

    def f(g):
        c, v = _binned(g)
        if c is None:
            return np.nan
        m = _weighted_moments(c, v)
        if m is None:
            return np.nan
        mean, var, w = m
        if var <= 0:
            return np.nan
        return float(np.average((c - mean) ** 3, weights=w) / var**1.5)

    return daily_apply(df_1m, f)


def compute_doc_kurt(df_1m: pd.DataFrame) -> pd.Series:
    """Excess kurtosis of the volume-weighted return distribution."""

    def f(g):
        c, v = _binned(g)
        if c is None:
            return np.nan
        m = _weighted_moments(c, v)
        if m is None:
            return np.nan
        mean, var, w = m
        if var <= 0:
            return np.nan
        return float(np.average((c - mean) ** 4, weights=w) / var**2 - 3.0)

    return daily_apply(df_1m, f)


def compute_doc_vol10_ratio(df_1m: pd.DataFrame) -> pd.Series:
    """Share of total volume in the 10 highest-volume bins."""

    def f(g):
        c, v = _binned(g)
        if c is None:
            return np.nan
        total = v.sum()
        if total == 0:
            return np.nan
        top10 = np.sort(v)[-10:].sum()
        return float(top10 / total)

    return daily_apply(df_1m, f)


FACTORS = {
    "doc_vol_pdf90": compute_doc_vol_pdf90,
    "doc_vol_pdf95": compute_doc_vol_pdf95,
    "doc_vol_pdf90bi": compute_doc_vol_pdf90bi,
    "doc_skew": compute_doc_skew,
    "doc_kurt": compute_doc_kurt,
    "doc_vol10_ratio": compute_doc_vol10_ratio,
}
