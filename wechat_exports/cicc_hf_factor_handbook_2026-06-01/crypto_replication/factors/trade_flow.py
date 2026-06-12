"""Trade-flow / smart-money factors (category: 资金流).

Only factors computable from 1-minute K-line data are implemented. Factors
requiring tick / order-flow data (``trade_bidAskRatio``, ``trade_CBuyRatio``,
``trade_CSellRatio``, ...) are skipped (see README).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import daily_apply


def _head_ratio(g: pd.DataFrame, n: int = 30) -> float:
    vol = g["volume"].to_numpy(dtype="float64")
    total = vol.sum()
    if total == 0 or len(vol) < n:
        return np.nan
    return float(vol[:n].sum() / total)


def compute_trade_headRatio(df_1m: pd.DataFrame) -> pd.Series:
    """First 30 bars' volume / total daily volume (top priority)."""
    return daily_apply(df_1m, _head_ratio)


def _tail_ratio(g: pd.DataFrame, n: int = 30) -> float:
    vol = g["volume"].to_numpy(dtype="float64")
    total = vol.sum()
    if total == 0 or len(vol) < n:
        return np.nan
    return float(vol[-n:].sum() / total)


def compute_trade_tailRatio(df_1m: pd.DataFrame) -> pd.Series:
    """Last 30 bars' volume / total daily volume."""
    return daily_apply(df_1m, _tail_ratio)


def _ret_ratio_segment(g: pd.DataFrame, n: int, head: bool) -> float:
    """sum(ret_i * vol_i / total_vol) over the first/last n bars."""
    ret = g["close"].pct_change().to_numpy(dtype="float64")
    vol = g["volume"].to_numpy(dtype="float64")
    total = vol.sum()
    if total == 0 or len(g) < n:
        return np.nan
    sel = slice(0, n) if head else slice(len(g) - n, len(g))
    r = ret[sel]
    v = vol[sel]
    mask = np.isfinite(r)
    return float(np.sum(r[mask] * v[mask] / total))


def compute_trade_top20retRatio(df_1m: pd.DataFrame) -> pd.Series:
    """First 20 bars (chronological): sum(ret_i * vol_i / total_vol) (top)."""
    return daily_apply(df_1m, lambda g: _ret_ratio_segment(g, 20, head=True))


def compute_trade_bottom20retRatio(df_1m: pd.DataFrame) -> pd.Series:
    """Last 20 bars (chronological): sum(ret_i * vol_i / total_vol)."""
    return daily_apply(df_1m, lambda g: _ret_ratio_segment(g, 20, head=False))


def compute_trade_top50retRatio(df_1m: pd.DataFrame) -> pd.Series:
    """First 50 bars (chronological): sum(ret_i * vol_i / total_vol)."""
    return daily_apply(df_1m, lambda g: _ret_ratio_segment(g, 50, head=True))


FACTORS = {
    "trade_headRatio": compute_trade_headRatio,
    "trade_tailRatio": compute_trade_tailRatio,
    "trade_top20retRatio": compute_trade_top20retRatio,
    "trade_bottom20retRatio": compute_trade_bottom20retRatio,
    "trade_top50retRatio": compute_trade_top50retRatio,
}
