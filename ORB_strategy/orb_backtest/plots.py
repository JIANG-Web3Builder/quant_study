from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import OrbConfig


def plot_equity_curves(results: dict[str, pd.DataFrame], config: OrbConfig, output_path: str | Path) -> Path:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 7))
    max_value = config.initial_capital
    for stop_type, df in results.items():
        if df.empty:
            continue
        clean = _prepare_curve_for_plot(df, config)
        if clean.empty:
            continue
        max_value = max(max_value, float(clean["aum"].max()))
        ax.plot(clean["day"], clean["aum"], linewidth=1.6, label=stop_type)
    ax.set_title(f"{config.orb_minutes}m-ORB | {config.ticker}")
    ax.set_ylabel("Account Value")
    ax.set_yscale("log", base=2)
    ticks = _account_value_ticks(config.initial_capital, max_value)
    ax.set_yticks(ticks)
    ax.set_yticklabels([_format_account_value(value) for value in ticks])
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper left")
    fig.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _prepare_curve_for_plot(equity_df: pd.DataFrame, config: OrbConfig) -> pd.DataFrame:
    clean = equity_df.dropna(subset=["day", "aum"]).copy()
    if clean.empty:
        return clean
    clean["day"] = pd.to_datetime(clean["day"])
    clean = clean.sort_values("day")
    initial = pd.DataFrame({"day": [pd.Timestamp(config.start_date)], "aum": [float(config.initial_capital)]})
    return pd.concat([initial, clean[["day", "aum"]]], ignore_index=True).drop_duplicates(
        subset=["day"], keep="first"
    )


def _account_value_ticks(initial_capital: float, max_value: float) -> list[float]:
    if initial_capital <= 0:
        initial_capital = 1
    ticks = [float(initial_capital)]
    while ticks[-1] < max_value:
        ticks.append(ticks[-1] * 2)
    return [int(tick) if float(tick).is_integer() else tick for tick in ticks]


def _format_account_value(value: float) -> str:
    value = float(value)
    if abs(value) >= 1_000_000:
        text = f"{value / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"${text}m"
    if abs(value) >= 1_000:
        text = f"{value / 1_000:.0f}"
        return f"${text}k"
    return f"${value:.0f}"
