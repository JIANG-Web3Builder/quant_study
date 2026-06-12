"""Aggregate IC + long-short results into a summary table and equity plots."""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .ic_analysis import ICResult  # noqa: E402
from .long_short import LongShortResult  # noqa: E402


def build_summary(results: dict[str, dict]) -> pd.DataFrame:
    """Build a summary DataFrame from a mapping ``factor_variant -> metrics``.

    Each value should contain the merged dicts from ``ICResult.as_dict`` and
    ``LongShortResult.as_dict``.
    """
    rows = []
    for name, metrics in results.items():
        row = {"factor": name}
        row.update(metrics)
        rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    cols = [
        "factor",
        "ic_mean",
        "icir",
        "win_rate",
        "ls_ann_return",
        "ls_sharpe",
        "ls_max_drawdown",
        "n_periods",
    ]
    cols = [c for c in cols if c in df.columns]
    df = df[cols].sort_values("icir", ascending=False, key=lambda s: s.abs())
    return df.reset_index(drop=True)


def save_summary(summary: pd.DataFrame, results_dir: str) -> str:
    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, "factor_summary.csv")
    summary.to_csv(path, index=False)
    return path


def plot_equity_curves(
    equity_curves: dict[str, pd.Series], results_dir: str, top_n: int = 15
) -> str:
    """Plot net-value (equity) curves for up to ``top_n`` factors."""
    os.makedirs(results_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 7))
    plotted = 0
    for name, curve in equity_curves.items():
        if curve is None or curve.empty:
            continue
        ax.plot(curve.index, curve.values, label=name, linewidth=1.2)
        plotted += 1
        if plotted >= top_n:
            break
    ax.set_title("Long-Short Net Value Curves")
    ax.set_xlabel("Date")
    ax.set_ylabel("Net value")
    ax.axhline(1.0, color="grey", linestyle="--", linewidth=0.8)
    if plotted:
        ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    path = os.path.join(results_dir, "long_short_equity_curves.png")
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def plot_ic_series(ic_series_map: dict[str, pd.Series], results_dir: str, top_n: int = 6) -> str:
    """Plot cumulative IC for the strongest factors (by |ICIR| ordering)."""
    os.makedirs(results_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    plotted = 0
    for name, ic in ic_series_map.items():
        if ic is None or ic.empty:
            continue
        ax.plot(ic.index, ic.cumsum().values, label=name, linewidth=1.2)
        plotted += 1
        if plotted >= top_n:
            break
    ax.set_title("Cumulative IC")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative IC")
    if plotted:
        ax.legend(fontsize=8)
    fig.tight_layout()
    path = os.path.join(results_dir, "cumulative_ic.png")
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def generate_report(
    ic_results: dict[str, ICResult],
    ls_results: dict[str, LongShortResult],
    results_dir: str,
) -> dict[str, str]:
    """Generate summary CSV and plots; return mapping of artifact -> path."""
    merged: dict[str, dict] = {}
    for name in ic_results:
        m = dict(ic_results[name].as_dict())
        if name in ls_results:
            m.update(ls_results[name].as_dict())
        merged[name] = m

    summary = build_summary(merged)
    summary_path = save_summary(summary, results_dir)

    # order plots by |ICIR| using the summary ordering
    ordered_names = list(summary["factor"]) if not summary.empty else list(ic_results)
    equity_curves = {
        n: ls_results[n].equity_curve for n in ordered_names if n in ls_results
    }
    ic_series_map = {
        n: ic_results[n].ic_series for n in ordered_names if n in ic_results
    }

    equity_path = plot_equity_curves(equity_curves, results_dir)
    ic_path = plot_ic_series(ic_series_map, results_dir)

    return {
        "summary": summary_path,
        "equity_curves": equity_path,
        "cumulative_ic": ic_path,
    }
