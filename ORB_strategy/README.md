# ORB Strategy Local Backtest

This folder contains a local Python implementation of the printed Colab notebook
`Backtesting the ORB Strategy with Free Alpaca Data`. The default config runs
the TQQQ strategy from `2020-01-01` through the latest complete Alpaca trading
day.

## Data

The CLI downloads Alpaca data automatically when cached CSV files are missing.
Set credentials in the process environment first:

```powershell
$env:APCA_API_KEY_ID = "..."
$env:APCA_API_SECRET_KEY = "..."
```

Cached files are written here:

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

Intraday data is downloaded with `timeframe=1Min`, `adjustment=raw`, and
`feed=sip`. Daily data is downloaded with `timeframe=1Day`, `adjustment=all`,
and `feed=sip`.

## Run

From `D:\quant_study\ORB_strategy`:

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m orb_backtest.cli --config configs/orb_tqqq.yaml
```

If data is missing, the CLI prints the exact files to create.

## Outputs

Results are written to `results/orb_tqqq_2020_latest/`:

- `equity_hl.csv`
- `equity_atr.csv`
- `summary_hl.csv` and `summary_hl.md`
- `summary_atr.csv` and `summary_atr.md`
- `monthly_returns_hl.csv` and `monthly_returns_hl.md`
- `monthly_returns_atr.csv` and `monthly_returns_atr.md`
- `equity_curves.png`

## Strategy Defaults

- Ticker: `TQQQ`
- Date range: `2020-01-01` to latest complete Alpaca trading day
- Opening range: first 5 one-minute bars
- Entry: next bar open
- Position sizing: fixed 1% equity risk per trade
- Max leverage: 4x
- Starting capital: `$10,000`
- Stop modes: opening range high/low, 5% ATR, and opening-range VWAP
- Profit target: 10R for opening range high/low mode; none for ATR mode
