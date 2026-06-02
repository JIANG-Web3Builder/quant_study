from __future__ import annotations

from datetime import date

import pandas as pd


def filter_regular_session_bars(intraday_df: pd.DataFrame) -> pd.DataFrame:
    """Keep bars before each NYSE session close; falls back to <=16:00 ET."""
    df = intraday_df.copy()
    if df.empty:
        return df

    df["datetime_et"] = pd.to_datetime(df["datetime_et"], utc=True).dt.tz_convert("America/New_York")
    df["day"] = df["datetime_et"].dt.date
    close_minutes = _nyse_close_minutes(set(df["day"]))
    bar_minutes = df["datetime_et"].dt.hour * 60 + df["datetime_et"].dt.minute
    thresholds = df["day"].map(close_minutes).fillna(16 * 60)
    return df[bar_minutes < thresholds].drop(columns=["day"]).reset_index(drop=True)


def _nyse_close_minutes(days: set[date]) -> dict[date, int]:
    if not days:
        return {}
    try:
        import exchange_calendars as xcals
    except ModuleNotFoundError:
        return {}

    cal = xcals.get_calendar("XNYS")
    start = min(days).isoformat()
    end = max(days).isoformat()
    schedule = cal.schedule.loc[start:end]
    close_map: dict[date, int] = {}
    for session, row in schedule.iterrows():
        session_day = session.date()
        if session_day not in days:
            continue
        close_ts = pd.Timestamp(row["market_close"])
        if close_ts.tzinfo is None:
            close_ts = close_ts.tz_localize("UTC")
        close_et = close_ts.tz_convert("America/New_York")
        close_map[session_day] = close_et.hour * 60 + close_et.minute
    return close_map
