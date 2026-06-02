# ORB Strategy Local Backtest

This folder contains a local Python implementation of the printed Colab notebook
`Backtesting the ORB Strategy with Free Alpaca Data`.

## Data

Place downloaded CSV files here:

- `data/alpaca/TQQQ_intraday.csv`
- `data/alpaca/TQQQ_daily.csv`

Intraday CSV columns:

- `datetime_et` or `caldt`
- `open`
- `high`
- `low`
- `close`
- `volume`

Daily CSV columns:

- `day`
- `open`
- `high`
- `low`
- `close`

The first version does not call Alpaca directly. After API access is available,
add a downloader that writes the same CSV shape and the backtest core can remain
unchanged.

## Run

From `D:\quant_study\ORB_strategy`:

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m orb_backtest.cli --config configs/orb_tqqq.yaml
```

If data is missing, the CLI prints the exact files to create.

## Outputs

Results are written to `results/orb_tqqq/`:

- `equity_hl.csv`
- `equity_atr.csv`
- `summary_hl.csv` and `summary_hl.md`
- `summary_atr.csv` and `summary_atr.md`
- `monthly_returns_hl.csv` and `monthly_returns_hl.md`
- `monthly_returns_atr.csv` and `monthly_returns_atr.md`
- `equity_curves.png`

## Strategy Defaults

- Ticker: `TQQQ`
- Date range: `2016-01-01` to `2026-04-20`
- Opening range: first 5 one-minute bars
- Entry: next bar open
- Position sizing: fixed 1% equity risk per trade
- Max leverage: 4x
- Stop modes: opening range high/low and 5% ATR
- Profit target: none
