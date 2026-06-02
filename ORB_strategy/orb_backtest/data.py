from __future__ import annotations

from pathlib import Path

import pandas as pd


INTRADAY_COLUMNS = ["datetime_et", "open", "high", "low", "close", "volume"]
DAILY_COLUMNS = ["day", "open", "high", "low", "close"]


def load_intraday_bars(path: str | Path, ticker: str | None = None) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(_missing_data_message(csv_path))

    df = pd.read_csv(csv_path)
    if ticker and "ticker" in df.columns:
        df = df[df["ticker"].astype(str).str.upper() == ticker.upper()].copy()

    dt_col = "datetime_et" if "datetime_et" in df.columns else "caldt" if "caldt" in df.columns else None
    if dt_col is None:
        raise ValueError("Intraday data missing required datetime column: datetime_et or caldt")
    missing = [col for col in ["open", "high", "low", "close", "volume"] if col not in df.columns]
    if missing:
        raise ValueError(f"Intraday data missing required columns: {missing}")

    out = df.rename(columns={dt_col: "datetime_et"})[INTRADAY_COLUMNS].copy()
    out["datetime_et"] = _to_new_york_time(out["datetime_et"])
    for col in ["open", "high", "low", "close", "volume"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["datetime_et", "open", "high", "low", "close"])
    return out.sort_values("datetime_et").reset_index(drop=True)


def load_daily_bars(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(_missing_data_message(csv_path))

    df = pd.read_csv(csv_path)
    missing = [col for col in DAILY_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Daily data missing required columns: {missing}")

    out = df[DAILY_COLUMNS].copy()
    out["day"] = pd.to_datetime(out["day"], errors="coerce").dt.date
    for col in ["open", "high", "low", "close"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=DAILY_COLUMNS)
    return out.sort_values("day").drop_duplicates(subset=["day"]).reset_index(drop=True)


def _to_new_york_time(values: pd.Series) -> pd.Series:
    def convert(value):
        if pd.isna(value):
            return pd.NaT
        timestamp = pd.Timestamp(value)
        if pd.isna(timestamp):
            return pd.NaT
        if timestamp.tzinfo is None:
            return timestamp.tz_localize("America/New_York")
        return timestamp.tz_convert("America/New_York")

    return values.map(convert)


def _missing_data_message(path: Path) -> str:
    return (
        f"Data file not found: {path}. Download API data first and place it at this path, "
        "or update configs/orb_tqqq.yaml to point to your CSV files."
    )
