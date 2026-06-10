from __future__ import annotations

from datetime import date
from math import floor, isfinite

import numpy as np
import pandas as pd

from .calendar import filter_regular_session_bars
from .config import OrbConfig


def run_orb_backtest(
    intraday_df: pd.DataFrame,
    config: OrbConfig,
    stop_type: str,
    atr_lookup: dict[date, float] | None = None,
) -> pd.DataFrame:
    stop_type = stop_type.upper()
    if stop_type not in {"HL", "ATR", "VWAP"}:
        raise ValueError("stop_type must be 'HL', 'ATR', or 'VWAP'")
    if stop_type == "ATR" and atr_lookup is None:
        raise ValueError("atr_lookup is required when stop_type='ATR'")

    bars = _prepare_bars(intraday_df)
    rows = []
    aum = float(config.initial_capital)

    for day, day_data in bars.groupby("day", sort=True):
        if day < config.start or day > config.end:
            continue
        day_data = day_data.sort_values("datetime_et").reset_index(drop=True)
        if len(day_data) <= config.orb_minutes:
            continue

        opening = day_data.iloc[: config.orb_minutes]
        decision_bar = opening.iloc[-1]
        first_open = float(opening.iloc[0]["open"])
        side = int(np.sign(float(decision_bar["close"]) - first_open))
        if side == 0:
            rows.append(_flat_row(day, aum, "flat"))
            continue

        entry_bar = day_data.iloc[config.orb_minutes]
        entry = float(entry_bar["open"])
        stop_distance, stop_price = _stop_distance(
            stop_type=stop_type,
            side=side,
            opening=opening,
            entry=entry,
            day=day,
            atr_lookup=atr_lookup,
            config=config,
        )
        if not isfinite(stop_distance) or stop_distance <= 0 or entry <= 0:
            continue

        shares = _position_size(aum, entry, stop_distance, config)
        if shares <= 0:
            rows.append(_flat_row(day, aum, "no_position"))
            continue

        post_entry = day_data.iloc[config.orb_minutes :].reset_index(drop=True)
        target_r = _target_r_for_stop(stop_type, config)
        pnl, exit_reason, exit_price = _trade_pnl(side, entry, stop_price, post_entry, target_r)
        gross_pnl = shares * pnl
        fees = shares * config.commission * 2
        net_pnl = gross_pnl - fees
        prev_aum = aum
        aum = aum + net_pnl
        rows.append(
            {
                "day": day,
                "side": side,
                "entry": entry,
                "stop_price": stop_price,
                "shares": shares,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "gross_pnl": gross_pnl,
                "fees": fees,
                "pnl": net_pnl,
                "aum": aum,
                "daily_return": (aum / prev_aum) - 1 if prev_aum else np.nan,
            }
        )

    return pd.DataFrame(rows)


def _prepare_bars(intraday_df: pd.DataFrame) -> pd.DataFrame:
    bars = intraday_df.copy()
    bars["datetime_et"] = pd.to_datetime(bars["datetime_et"], utc=True).dt.tz_convert("America/New_York")
    for col in ["open", "high", "low", "close"]:
        bars[col] = pd.to_numeric(bars[col], errors="coerce")
    bars = bars.dropna(subset=["datetime_et", "open", "high", "low", "close"])
    bars = filter_regular_session_bars(bars)
    bars["day"] = bars["datetime_et"].dt.date
    return bars.sort_values("datetime_et")


def _stop_distance(
    stop_type: str,
    side: int,
    opening: pd.DataFrame,
    entry: float,
    day: date,
    atr_lookup: dict[date, float] | None,
    config: OrbConfig,
) -> tuple[float, float]:
    if stop_type == "ATR":
        atr_pct = atr_lookup.get(day, np.nan) if atr_lookup else np.nan
        if pd.isna(atr_pct):
            return np.nan, np.nan
        distance = float(config.stop_atr) * float(atr_pct)
        stop_price = entry * (1 - distance) if side == 1 else entry * (1 + distance)
        return distance, stop_price

    if stop_type == "VWAP":
        stop_price = _opening_vwap(opening)
        if side == 1 and stop_price >= entry:
            return np.nan, np.nan
        if side == -1 and stop_price <= entry:
            return np.nan, np.nan
        return abs((entry - stop_price) / entry), stop_price

    if side == 1:
        stop_price = float(opening["low"].min())
        return abs((entry - stop_price) / entry), stop_price
    stop_price = float(opening["high"].max())
    return abs((stop_price - entry) / entry), stop_price


def _position_size(aum: float, entry: float, stop_distance: float, config: OrbConfig) -> int:
    risk_shares = floor(aum * config.risk / (entry * stop_distance))
    leverage_shares = floor(config.max_leverage * aum / entry)
    return max(0, min(risk_shares, leverage_shares))


def _opening_vwap(opening: pd.DataFrame) -> float:
    volume = pd.to_numeric(opening["volume"], errors="coerce").fillna(0)
    close = pd.to_numeric(opening["close"], errors="coerce")
    total_volume = float(volume.sum())
    if total_volume <= 0:
        return float(close.mean())
    return float((close * volume).sum() / total_volume)


def _target_r_for_stop(stop_type: str, config: OrbConfig) -> float | None:
    if stop_type == "HL":
        return config.target_r_hl
    return None


def _trade_pnl(
    side: int,
    entry: float,
    stop_price: float,
    post_entry: pd.DataFrame,
    target_r: float | None = None,
) -> tuple[float, str, float]:
    stop_distance = abs((entry - stop_price) / entry)
    use_target = target_r is not None and isfinite(target_r) and target_r > 0 and stop_distance > 0
    if side == 1:
        target_price = entry * (1 + target_r * stop_distance) if use_target else np.nan
        stop_hits = post_entry["low"].to_numpy() <= stop_price
        target_hits = post_entry["high"].to_numpy() >= target_price if use_target else np.zeros(len(post_entry), dtype=bool)
        if stop_hits.any() and target_hits.any():
            idx_stop = int(np.argmax(stop_hits))
            idx_target = int(np.argmax(target_hits))
            if idx_target < idx_stop:
                exit_price = max(target_price, float(post_entry.iloc[idx_target]["open"]))
                return exit_price - entry, "target", exit_price
            exit_price = min(stop_price, float(post_entry.iloc[idx_stop]["open"]))
            return exit_price - entry, "stop", exit_price
        if stop_hits.any():
            idx = int(np.argmax(stop_hits))
            exit_price = min(stop_price, float(post_entry.iloc[idx]["open"]))
            return exit_price - entry, "stop", exit_price
        if target_hits.any():
            idx = int(np.argmax(target_hits))
            exit_price = max(target_price, float(post_entry.iloc[idx]["open"]))
            return exit_price - entry, "target", exit_price
        exit_price = float(post_entry.iloc[-1]["close"])
        return exit_price - entry, "close", exit_price

    target_price = entry * (1 - target_r * stop_distance) if use_target else np.nan
    stop_hits = post_entry["high"].to_numpy() >= stop_price
    target_hits = post_entry["low"].to_numpy() <= target_price if use_target else np.zeros(len(post_entry), dtype=bool)
    if stop_hits.any() and target_hits.any():
        idx_stop = int(np.argmax(stop_hits))
        idx_target = int(np.argmax(target_hits))
        if idx_target < idx_stop:
            exit_price = min(target_price, float(post_entry.iloc[idx_target]["open"]))
            return entry - exit_price, "target", exit_price
        exit_price = max(stop_price, float(post_entry.iloc[idx_stop]["open"]))
        return entry - exit_price, "stop", exit_price
    if stop_hits.any():
        idx = int(np.argmax(stop_hits))
        exit_price = max(stop_price, float(post_entry.iloc[idx]["open"]))
        return entry - exit_price, "stop", exit_price
    if target_hits.any():
        idx = int(np.argmax(target_hits))
        exit_price = min(target_price, float(post_entry.iloc[idx]["open"]))
        return entry - exit_price, "target", exit_price
    exit_price = float(post_entry.iloc[-1]["close"])
    return entry - exit_price, "close", exit_price


def _flat_row(day: date, aum: float, reason: str) -> dict[str, object]:
    return {
        "day": day,
        "side": 0,
        "entry": np.nan,
        "stop_price": np.nan,
        "shares": 0,
        "exit_price": np.nan,
        "exit_reason": reason,
        "gross_pnl": 0.0,
        "fees": 0.0,
        "pnl": 0.0,
        "aum": aum,
        "daily_return": 0.0,
    }
