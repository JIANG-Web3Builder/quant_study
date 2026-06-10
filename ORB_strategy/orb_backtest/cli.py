from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import pandas as pd

from .alpaca import AlpacaDataError, download_alpaca_csvs, resolve_end_date
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
    resolved_end = resolve_end_date(config.end_date)
    config = replace(config, end_date=resolved_end.isoformat())
    intraday_path = config.resolve_intraday_path(base_dir)
    daily_path = config.resolve_daily_path(base_dir)
    missing = [path for path in [intraday_path, daily_path] if not path.exists()]
    if missing:
        print("Missing required CSV data files; attempting Alpaca download:")
        for path in missing:
            print(f"  - {path}")
        try:
            download_alpaca_csvs(config.ticker, config.start_date, resolved_end, intraday_path.parent)
        except AlpacaDataError as exc:
            print(str(exc))
            return 2

        missing = [path for path in [intraday_path, daily_path] if not path.exists()]
        if missing:
            print("Alpaca download completed, but expected CSV files are still missing:")
            for path in missing:
                print(f"  - {path}")
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
        (output_dir / f"summary_{stop_type.lower()}.md").write_text(_to_markdown(summary), encoding="utf-8")
        (output_dir / f"monthly_returns_{stop_type.lower()}.md").write_text(_to_markdown(monthly), encoding="utf-8")
        _print_console_summary(stop_type.upper(), result, summary)

    plot_equity_curves(results, config, output_dir / "equity_curves.png")
    print(f"ORB backtest finished. Results written to {output_dir}")
    return 0


def _print_console_summary(stop_type: str, result: pd.DataFrame, summary: pd.DataFrame) -> None:
    if result.empty:
        print(f"{stop_type}: no trades")
        return
    final_capital = float(result.sort_values("day").iloc[-1]["aum"])
    values = summary["Value"].to_dict()
    print(
        f"{stop_type}: final capital ${final_capital:,.2f} | "
        f"Total Return {values.get('Total Return (%)', 'nan')}% | "
        f"CAGR {values.get('CAGR (%)', 'nan')}% | "
        f"Volatility {values.get('Volatility (%)', 'nan')}% | "
        f"Sharpe {values.get('Sharpe Ratio', 'nan')} | "
        f"Max Drawdown {values.get('Max Drawdown (%)', 'nan')}%"
    )


def _to_markdown(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown()
    except ImportError:
        return df.to_csv()


if __name__ == "__main__":
    raise SystemExit(main())
