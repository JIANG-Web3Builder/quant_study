"""Factor variant handling.

Each base factor produces a daily-frequency ``pd.Series`` (index = date). The
report applies four variants on top of every base factor, mirroring the
``_o`` / ``_m`` / ``_std`` / ``_z`` suffixes used throughout the CICC HF factor
handbook:

- ``_o``   raw daily value (the factor value of the day itself)
- ``_m``   trailing 20-day rolling mean
- ``_std`` trailing 20-day rolling standardization ``(x - mean) / std``
- ``_z``   cross-sectional z-score across all symbols on the same date

Cross-sectional variants operate on a wide DataFrame (index = date,
columns = symbol); time-series variants operate per symbol.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

VARIANT_SUFFIXES = ("_o", "_m", "_std", "_z")

# Minimum number of 1-minute bars a (symbol, day) must have to be considered a
# valid trading day. Days with fewer bars are dropped to avoid noise from
# missing data (a full UTC day has 1440 bars).
MIN_BARS_PER_DAY = 100


def ensure_minute_frame(df_1m: pd.DataFrame) -> pd.DataFrame:
    """Return a copy indexed by ``open_time`` (DatetimeIndex), sorted in time.

    Accepts a frame that is either already indexed by ``open_time`` or has an
    ``open_time`` column. Adds a ``date`` column with the UTC calendar date.
    """
    df = df_1m.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        if "open_time" in df.columns:
            df = df.set_index("open_time")
        else:
            raise ValueError("df_1m must be indexed by open_time or contain it")
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()
    df["date"] = df.index.normalize().tz_localize(None)
    return df


def daily_apply(
    df_1m: pd.DataFrame,
    func,
    min_bars: int = MIN_BARS_PER_DAY,
) -> pd.Series:
    """Group a minute frame by UTC date and apply ``func`` to each day's frame.

    ``func`` receives the per-day minute DataFrame (sorted by time) and returns
    a scalar. Days with fewer than ``min_bars`` rows are skipped (value NaN).
    The result is a daily Series indexed by ``date`` (tz-naive Timestamps).
    """
    df = ensure_minute_frame(df_1m)
    out: dict[pd.Timestamp, float] = {}
    for day, g in df.groupby("date", sort=True):
        if len(g) < min_bars:
            out[day] = np.nan
            continue
        try:
            out[day] = float(func(g))
        except (ValueError, ZeroDivisionError, FloatingPointError):
            out[day] = np.nan
    return pd.Series(out, dtype="float64").sort_index()


def minute_returns(g: pd.DataFrame) -> np.ndarray:
    """Simple minute close-to-close returns within a day's frame."""
    close = g["close"].to_numpy(dtype="float64")
    return close[1:] / close[:-1] - 1.0


def apply_variants(factor_series: pd.Series, window: int = 20) -> dict[str, pd.Series]:
    """Apply the time-series variants to a single symbol's daily factor series.

    The ``_z`` variant is cross-sectional and cannot be computed from a single
    symbol; it is returned here as a copy of the raw series so it can be
    z-scored later across symbols (see :func:`cross_sectional_zscore`).

    Returns a dict keyed by ``{'_o', '_m', '_std', '_z'}``.
    """
    s = factor_series.astype("float64").sort_index()
    rolling_mean = s.rolling(window, min_periods=max(2, window // 2)).mean()
    rolling_std = s.rolling(window, min_periods=max(2, window // 2)).std()

    standardized = (s - rolling_mean) / rolling_std
    standardized = standardized.replace([float("inf"), float("-inf")], pd.NA)

    return {
        "_o": s,
        "_m": rolling_mean,
        "_std": standardized.astype("float64"),
        # placeholder; the actual cross-sectional z-score is applied later once
        # all symbols are aligned into a wide DataFrame.
        "_z": s,
    }


def cross_sectional_zscore(factor_df: pd.DataFrame) -> pd.DataFrame:
    """Z-score each row (date) of a wide factor DataFrame across symbols.

    ``factor_df``: index = date, columns = symbol.
    """
    mean = factor_df.mean(axis=1)
    std = factor_df.std(axis=1)
    z = factor_df.sub(mean, axis=0).div(std, axis=0)
    return z.replace([float("inf"), float("-inf")], pd.NA)


def variant_panels(
    base_panel: pd.DataFrame, window: int = 20
) -> dict[str, pd.DataFrame]:
    """Build the four variant panels from a base wide panel.

    ``base_panel``: index = date, columns = symbol, values = raw daily factor.

    Returns a dict mapping each variant suffix to a wide DataFrame. The ``_o``,
    ``_m`` and ``_std`` panels are computed per-column (per symbol); the ``_z``
    panel is the cross-sectional z-score of the raw panel.
    """
    panel = base_panel.sort_index()
    minp = max(2, window // 2)

    rolling_mean = panel.rolling(window, min_periods=minp).mean()
    rolling_std = panel.rolling(window, min_periods=minp).std()
    standardized = (panel - rolling_mean) / rolling_std
    standardized = standardized.replace([float("inf"), float("-inf")], pd.NA)

    return {
        "_o": panel,
        "_m": rolling_mean,
        "_std": standardized,
        "_z": cross_sectional_zscore(panel),
    }
