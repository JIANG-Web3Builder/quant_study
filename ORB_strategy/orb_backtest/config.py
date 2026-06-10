from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OrbConfig:
    ticker: str = "TQQQ"
    start_date: str = "2016-01-01"
    end_date: str = "2026-04-20"
    orb_minutes: int = 5
    risk: float = 0.01
    max_leverage: float = 4.0
    initial_capital: float = 10_000.0
    commission: float = 0.0005
    atr_period: int = 14
    stop_atr: float = 0.05
    target_r_hl: float | None = 10.0
    intraday_path: str = "data/alpaca/{ticker}_intraday.csv"
    daily_path: str = "data/alpaca/{ticker}_daily.csv"
    output_dir: str = "results/orb_tqqq"
    active_stop_types: tuple[str, ...] = ("HL", "ATR")

    @property
    def start(self):
        import pandas as pd

        return pd.Timestamp(self.start_date).date()

    @property
    def end(self):
        import pandas as pd

        return pd.Timestamp(self.end_date).date()

    def resolve_intraday_path(self, base_dir: Path) -> Path:
        return base_dir / self.intraday_path.format(ticker=self.ticker)

    def resolve_daily_path(self, base_dir: Path) -> Path:
        return base_dir / self.daily_path.format(ticker=self.ticker)

    def resolve_output_dir(self, base_dir: Path) -> Path:
        return base_dir / self.output_dir


def load_config(path: str | Path) -> OrbConfig:
    config_path = Path(path)
    data = _load_mapping(config_path)
    return OrbConfig(**data)


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        loaded = yaml.safe_load(text) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Config must contain a mapping: {path}")
        return loaded
    except ModuleNotFoundError:
        return _load_simple_yaml(text, path)


def _load_simple_yaml(text: str, path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"Unsupported config line in {path}: {raw_line}")
        key, raw_value = line.split(":", 1)
        data[key.strip()] = _parse_scalar(raw_value.strip())
    return data


def _parse_scalar(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return ()
        return tuple(_parse_scalar(part.strip()) for part in inner.split(","))
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none", "~"}:
        return None
    try:
        if any(ch in value for ch in [".", "e", "E"]):
            return float(value)
        return int(value)
    except ValueError:
        return value
