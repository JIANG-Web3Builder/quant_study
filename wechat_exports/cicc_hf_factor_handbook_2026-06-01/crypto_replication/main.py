"""End-to-end crypto factor replication pipeline.

Pipeline:
    1. download (or reuse) 1-minute Binance data for the chosen symbols
    2. compute every base factor per symbol -> daily panel (date x symbol)
    3. build the 4 variants (_o / _m / _std / _z) per base factor
    4. derive period forward returns from daily closes at the chosen frequency
    5. run IC analysis + long-short backtest for each factor variant
    6. write a summary table and plots into results/

Run:
    python main.py --freq monthly
    python main.py --symbols BTCUSDT ETHUSDT --factors mmt_ols_beta_mean vol_upVol
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd
from tqdm import tqdm

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from backtest import ic_analysis, long_short, report  # noqa: E402
from data import binance_downloader as bd  # noqa: E402
from factors import DIRECTIONS, REGISTRY, base  # noqa: E402

DATA_DIR = os.path.join(HERE, "data")
RESULTS_DIR = os.path.join(HERE, "results")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Crypto HF factor replication")
    p.add_argument(
        "--symbols",
        nargs="*",
        default=None,
        help="Symbols (default: auto top-50 USDT spot pairs)",
    )
    p.add_argument("--start", default=None, help="Start date, e.g. 2024-01-01")
    p.add_argument("--end", default=None, help="End date, e.g. 2024-04-01")
    p.add_argument("--days", type=int, default=90, help="Lookback days if no start/end")
    p.add_argument(
        "--factors",
        nargs="*",
        default=None,
        help="Base factor names to compute (default: all)",
    )
    p.add_argument(
        "--freq",
        choices=["weekly", "monthly"],
        default="monthly",
        help="Rebalance frequency",
    )
    p.add_argument("--top-n", type=int, default=50, help="Number of symbols to auto-pick")
    p.add_argument(
        "--skip-download",
        action="store_true",
        help="Use already-saved parquet data and do not hit the API",
    )
    return p.parse_args(argv)


def resolve_symbols(args: argparse.Namespace) -> list[str]:
    if args.symbols:
        return args.symbols
    if args.skip_download:
        raw_dir = os.path.join(DATA_DIR, "raw")
        if not os.path.isdir(raw_dir):
            return []
        syms = sorted({f.split("_1m_")[0] for f in os.listdir(raw_dir) if "_1m_" in f})
        return syms
    return bd.get_top_usdt_symbols(args.top_n)


def resolve_dates(args: argparse.Namespace) -> tuple[str, str]:
    if args.start and args.end:
        return args.start, args.end
    return bd.default_date_range(args.days)


def compute_base_panels(
    symbols: list[str], factor_names: list[str]
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Compute base factor panels and a daily close price panel.

    Returns ``(panels, price_panel)`` where ``panels`` maps factor name to a
    wide DataFrame (date x symbol) and ``price_panel`` is daily last close.
    """
    factor_cols: dict[str, dict[str, pd.Series]] = {f: {} for f in factor_names}
    close_cols: dict[str, pd.Series] = {}

    for symbol in tqdm(symbols, desc="factors"):
        try:
            df_1m = bd.load_minute_data(symbol, DATA_DIR)
        except FileNotFoundError:
            continue
        if df_1m.empty:
            continue

        prepared = base.ensure_minute_frame(df_1m)
        counts = prepared.groupby("date").size()
        valid_days = counts[counts >= base.MIN_BARS_PER_DAY].index
        daily_close = (
            prepared.groupby("date")["close"].last().reindex(valid_days)
        )
        close_cols[symbol] = daily_close

        for fname in factor_names:
            series = REGISTRY[fname](df_1m)
            factor_cols[fname][symbol] = series

    panels = {
        f: pd.DataFrame(cols).sort_index()
        for f, cols in factor_cols.items()
        if cols
    }
    price_panel = pd.DataFrame(close_cols).sort_index()
    return panels, price_panel


def run_backtests(
    panels: dict[str, pd.DataFrame],
    price_panel: pd.DataFrame,
    freq: str,
) -> tuple[dict, dict]:
    rebal_dates = ic_analysis.select_rebalance_dates(price_panel.index, freq)
    fwd = ic_analysis.period_forward_returns(price_panel, rebal_dates)

    ic_results: dict = {}
    ls_results: dict = {}

    for fname, base_panel in panels.items():
        direction = DIRECTIONS.get(fname, 1)
        variants = base.variant_panels(base_panel)
        for suffix, vpanel in variants.items():
            name = f"{fname}{suffix}"
            f_at_rebal = vpanel.reindex(rebal_dates)
            ic_results[name] = ic_analysis.compute_ic(f_at_rebal, fwd)
            ls_results[name] = long_short.run_long_short(
                f_at_rebal, fwd, freq=freq, direction=direction
            )
    return ic_results, ls_results


def main(argv=None) -> int:
    args = parse_args(argv)
    symbols = resolve_symbols(args)
    if not symbols:
        print("No symbols resolved. Provide --symbols or remove --skip-download.")
        return 1

    start, end = resolve_dates(args)
    print(f"Symbols: {len(symbols)} | Range: {start} -> {end} | Freq: {args.freq}")

    if not args.skip_download:
        bd.download_symbols(symbols, start, end, save_dir=DATA_DIR)

    factor_names = args.factors or list(REGISTRY.keys())
    unknown = [f for f in factor_names if f not in REGISTRY]
    if unknown:
        print(f"Unknown factors ignored: {unknown}")
        factor_names = [f for f in factor_names if f in REGISTRY]

    panels, price_panel = compute_base_panels(symbols, factor_names)
    if not panels or price_panel.empty:
        print("No factor/price data computed. Check that data was downloaded.")
        return 1

    ic_results, ls_results = run_backtests(panels, price_panel, args.freq)
    artifacts = report.generate_report(ic_results, ls_results, RESULTS_DIR)

    print("\nArtifacts written:")
    for k, v in artifacts.items():
        print(f"  {k}: {v}")

    summary = pd.read_csv(artifacts["summary"])
    print("\nTop factors by |ICIR|:")
    print(summary.head(15).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
