from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd


def compute_atr_pct_lookup(daily_df: pd.DataFrame, period: int = 14) -> dict[date, float]:
    df = daily_df.sort_values("day").copy()
    df["day"] = pd.to_datetime(df["day"]).dt.date
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period, min_periods=period).mean()
    atr_pct = (atr / df["open"]).shift(1)
    result = dict(zip(df["day"], atr_pct))
    return {key: (float(value) if not pd.isna(value) else np.nan) for key, value in result.items()}
