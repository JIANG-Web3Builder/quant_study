"""Download historical 1-minute klines from the public Binance REST API.

No API key is required. Data is paginated from ``/api/v3/klines`` (max 1000
bars per request) and stored as parquet under ``data/raw/``.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

try:  # tqdm is optional at import time
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(x, **kwargs):
        return x

BASE_URL = "https://api.binance.com"
KLINES_ENDPOINT = "/api/v3/klines"
TICKER_ENDPOINT = "/api/v3/ticker/24hr"

KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]

NUMERIC_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "trades",
    "taker_buy_base",
    "taker_buy_quote",
]


def _to_millis(dt_str: str) -> int:
    dt = pd.Timestamp(dt_str, tz="UTC")
    return int(dt.timestamp() * 1000)


def _request(url: str, params: dict, max_retries: int = 5):
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 429:  # rate limited
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    return None


def get_top_usdt_symbols(top_n: int = 50) -> list[str]:
    """Return the top ``top_n`` USDT spot pairs by 24h quote volume."""
    data = _request(BASE_URL + TICKER_ENDPOINT, params={})
    rows = []
    for d in data:
        sym = d.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        # skip leveraged tokens / non-spot style symbols
        if any(tag in sym for tag in ("UP", "DOWN", "BULL", "BEAR")):
            continue
        try:
            qv = float(d.get("quoteVolume", 0.0))
        except (TypeError, ValueError):
            qv = 0.0
        rows.append((sym, qv))
    rows.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in rows[:top_n]]


def download_klines(symbol: str, start: str, end: str, interval: str = "1m") -> pd.DataFrame:
    """Paginate 1-minute klines for ``symbol`` between ``start`` and ``end``."""
    start_ms = _to_millis(start)
    end_ms = _to_millis(end)
    all_rows = []
    cursor = start_ms
    while cursor < end_ms:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": 1000,
        }
        batch = _request(BASE_URL + KLINES_ENDPOINT, params=params)
        if not batch:
            break
        all_rows.extend(batch)
        last_open = batch[-1][0]
        cursor = last_open + 60_000  # next minute
        if len(batch) < 1000:
            break
        time.sleep(0.25)  # be polite to the API

    if not all_rows:
        return pd.DataFrame(columns=KLINE_COLUMNS)

    df = pd.DataFrame(all_rows, columns=KLINE_COLUMNS)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.drop(columns=["ignore"])
    df = df.drop_duplicates(subset="open_time").sort_values("open_time")
    return df.reset_index(drop=True)


def _raw_path(save_dir: str, symbol: str, start: str, end: str) -> str:
    raw_dir = os.path.join(save_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    s = start.replace("-", "").replace(":", "").replace(" ", "")[:8]
    e = end.replace("-", "").replace(":", "").replace(" ", "")[:8]
    return os.path.join(raw_dir, f"{symbol}_1m_{s}_{e}.parquet")


def download_symbols(
    symbols: list[str],
    start: str,
    end: str,
    save_dir: str,
) -> dict[str, str]:
    """Download and save 1-minute data for each symbol.

    Returns a mapping ``symbol -> parquet path`` for the symbols that produced
    a non-empty frame.
    """
    saved: dict[str, str] = {}
    for symbol in tqdm(symbols, desc="download"):
        path = _raw_path(save_dir, symbol, start, end)
        if os.path.exists(path):
            saved[symbol] = path
            continue
        df = download_klines(symbol, start, end)
        if df.empty:
            continue
        df.to_parquet(path, index=False)
        saved[symbol] = path
    return saved


def _find_parquet(symbol: str, data_dir: str) -> str | None:
    raw_dir = os.path.join(data_dir, "raw")
    if not os.path.isdir(raw_dir):
        return None
    matches = sorted(
        f for f in os.listdir(raw_dir) if f.startswith(f"{symbol}_1m_") and f.endswith(".parquet")
    )
    if not matches:
        return None
    return os.path.join(raw_dir, matches[-1])


def load_minute_data(symbol: str, data_dir: str) -> pd.DataFrame:
    """Load saved 1-minute data for ``symbol``, indexed by ``open_time``."""
    path = _find_parquet(symbol, data_dir)
    if path is None:
        raise FileNotFoundError(f"No saved parquet for {symbol} under {data_dir}/raw")
    df = pd.read_parquet(path)
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    return df.set_index("open_time").sort_index()


def default_date_range(days: int = 90) -> tuple[str, str]:
    """Return (start, end) ISO strings covering the last ``days`` days (UTC)."""
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    fmt = "%Y-%m-%d %H:%M:%S"
    return start.strftime(fmt), end.strftime(fmt)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    s, e = default_date_range(90)
    syms = get_top_usdt_symbols(50)
    print(f"Top symbols: {syms[:10]} ... ({len(syms)} total)")
    download_symbols(syms, s, e, save_dir=here)
