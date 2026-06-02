from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .config import OrbConfig, load_config
from .data import load_daily_bars, load_intraday_bars
from .indicators import compute_atr_pct_lookup
from .engine import run_orb_backtest
from .metrics import monthly_return_table, summarize_performance
from .plots import plot_equity_curves


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local ORB strategy backtest.")
    parser.add_argument("--config", default="configs/orb_tqqq.yaml", help="Path to YAML config.")
    args = parser.parse_args(argv)

    base_dir = Path.cwd()
    config = load_config(base_dir / args.config)
    return run_from_config(config, base_dir)


def run_from_config(config: OrbConfig, base_dir: Path) -> int:
    intraday_path = config.resolve_intraday_path(base_dir)
    daily_path = config.resolve_daily_path(base_dir)
    missing = [path for path in [intraday_path, daily_path] if not path.exists()]
    if missing:
        print("Missing required CSV data files:")
        for path in missing:
            print(f"  - {path}")
        print("Download API data first, or edit the config paths, then run again.")
        return 2

    intraday = load_intraday_bars(intraday_path, ticker=config.ticker)
    daily = load_daily_bars(daily_path)
    atr_lookup = compute_atr_pct_lookup(daily, period=config.atr_period)
    output_dir = config.resolve_output_dir(base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, pd.DataFrame] = {}
    for stop_type in config.active_stop_types:
        lookup = atr_lookup if stop_type.upper() == "ATR" else None
        result = run_orb_backtest(intraday, config, stop_type=stop_type, atr_lookup=lookup)
        results[stop_type.upper()] = result
        result.to_csv(output_dir / f"equity_{stop_type.lower()}.csv", index=False)
        summary = summarize_performance(result, initial_capital=config.initial_capital)
        monthly = monthly_return_table(result, initial_capital=config.initial_capital)
        summary.to_csv(output_dir / f"summary_{stop_type.lower()}.csv")
        monthly.to_csv(output_dir / f"monthly_returns_{stop_type.lower()}.csv")
        (output_dir / f"summary_{stop_type.lower()}.md").write_text(summary.to_markdown(), encoding="utf-8")
        (output_dir / f"monthly_returns_{stop_type.lower()}.md").write_text(monthly.to_markdown(), encoding="utf-8")

    plot_equity_curves(results, config, output_dir / "equity_curves.png")
    print(f"ORB backtest finished. Results written to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
