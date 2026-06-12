"""Liquidity factors (category: 流动性).

Only factors computable from 1-minute K-line data are implemented. Factors that
require tick / order-book / call-auction data (``liq_spread``,
``liq_firstCallR``, depth factors, ...) are skipped (see README).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import daily_apply


def _amihud_1min(g: pd.DataFrame) -> float:
    ret = g["close"].pct_change().to_numpy(dtype="float64")
    qv = g["quote_volume"].to_numpy(dtype="float64")
    mask = (qv > 0) & np.isfinite(ret)
    if mask.sum() < 2:
        return np.nan
    illiq = np.abs(ret[mask]) / qv[mask]
    return float(np.mean(illiq))


def compute_liq_amihud_1min(df_1m: pd.DataFrame) -> pd.Series:
    """Minute-level Amihud illiquidity (top priority).

    illiq_i = |ret_i| / quote_volume_i ; daily value = mean over the day.
    Bars with quote_volume == 0 are filtered out.
    """
    return daily_apply(df_1m, _amihud_1min)


def _closevol(g: pd.DataFrame) -> float:
    vol = g["volume"].to_numpy(dtype="float64")
    if len(vol) < 3:
        return np.nan
    return float(vol[-3:].sum())


def compute_liq_closevol(df_1m: pd.DataFrame) -> pd.Series:
    """Sum of volume over the last 3 minute bars of the day."""
    return daily_apply(df_1m, _closevol)


FACTORS = {
    "liq_amihud_1min": compute_liq_amihud_1min,
    "liq_closevol": compute_liq_closevol,
}
