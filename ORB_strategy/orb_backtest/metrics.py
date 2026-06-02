from __future__ import annotations

import numpy as np
import pandas as pd


def summarize_performance(equity_df: pd.DataFrame, initial_capital: float | None = None) -> pd.DataFrame:
    if equity_df.empty:
        return pd.DataFrame({"Metric": [], "Value": []}).set_index("Metric")
    df = equity_df.sort_values("day").copy()
    df["day"] = pd.to_datetime(df["day"])
    aum = df["aum"].astype(float)
    start_aum = float(initial_capital if initial_capital is not None else aum.iloc[0])
    daily_returns = aum.pct_change()
    if initial_capital is not None and len(aum) > 0:
        daily_returns.iloc[0] = aum.iloc[0] / initial_capital - 1
    daily_returns = daily_returns.replace([np.inf, -np.inf], np.nan).dropna()

    total_return = aum.iloc[-1] / start_aum - 1
    trading_days = max(len(df), 1)
    cagr = (aum.iloc[-1] / start_aum) ** (252 / trading_days) - 1
    volatility = daily_returns.std(ddof=0) * np.sqrt(252) if len(daily_returns) else np.nan
    sharpe = daily_returns.mean() / daily_returns.std(ddof=0) * np.sqrt(252) if daily_returns.std(ddof=0) else np.nan
    drawdown = aum / aum.cummax() - 1

    values = {
        "Total Return (%)": total_return * 100,
        "CAGR (%)": cagr * 100,
        "Volatility (%)": volatility * 100 if not pd.isna(volatility) else np.nan,
        "Sharpe Ratio": sharpe,
        "Max Drawdown (%)": drawdown.min() * 100,
    }
    return pd.DataFrame(
        {"Metric": values.keys(), "Value": [_format_number(v) for v in values.values()]}
    ).set_index("Metric")


def monthly_return_table(equity_df: pd.DataFrame, initial_capital: float | None = None) -> pd.DataFrame:
    if equity_df.empty:
        return pd.DataFrame()
    df = equity_df.sort_values("day").copy()
    df["day"] = pd.to_datetime(df["day"])
    df = df.set_index("day")
    month_end = df["aum"].resample("ME").last().dropna()
    if month_end.empty:
        return pd.DataFrame()
    base = initial_capital if initial_capital is not None else month_end.iloc[0]
    prev = month_end.shift(1)
    prev.iloc[0] = base
    monthly = month_end / prev - 1
    out = monthly.to_frame("return")
    out["year"] = out.index.year
    out["month"] = out.index.strftime("%b")
    pivot = out.pivot(index="year", columns="month", values="return")
    order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    pivot = pivot.reindex(columns=order)
    year_total = month_end.groupby(month_end.index.year).agg(lambda values: values.iloc[-1])
    year_base = year_total.shift(1)
    year_base.iloc[0] = base
    pivot["Year Total"] = year_total / year_base - 1
    return pivot.map(lambda value: "" if pd.isna(value) else f"{value * 100:.2f}%")


def _format_number(value: float) -> str:
    if pd.isna(value):
        return "nan"
    return f"{value:.2f}"
