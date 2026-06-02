from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import OrbConfig


def plot_equity_curves(results: dict[str, pd.DataFrame], config: OrbConfig, output_path: str | Path) -> Path:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 7))
    for stop_type, df in results.items():
        if df.empty:
            continue
        clean = df.dropna(subset=["day", "aum"]).copy()
        clean["day"] = pd.to_datetime(clean["day"])
        ax.plot(clean["day"], clean["aum"], linewidth=1.6, label=stop_type)
    ax.set_title(f"{config.orb_minutes}m-ORB | {config.ticker}")
    ax.set_ylabel("Account Value")
    ax.set_yscale("log", base=2)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper left")
    fig.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
