from __future__ import annotations

from pathlib import Path

import pandas as pd

from orb_backtest import cli
from orb_backtest.config import OrbConfig


def _write_minute_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for minute in range(6):
        rows.append(
            {
                "datetime_et": pd.Timestamp(f"2024-01-02 09:{30 + minute:02d}", tz="America/New_York"),
                "open": 100.0 + minute,
                "high": 101.0 + minute,
                "low": 99.0 + minute,
                "close": 100.5 + minute,
                "volume": 1000,
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)


def _write_daily_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "day": pd.date_range("2023-12-01", periods=40, freq="B").date,
            "open": [100.0] * 40,
            "high": [102.0] * 40,
            "low": [98.0] * 40,
            "close": [101.0] * 40,
        }
    ).to_csv(path, index=False)


def test_run_from_config_downloads_missing_alpaca_csvs(monkeypatch, tmp_path: Path):
    calls = []

    def fake_download(symbol, start_date, end_date, output_dir):
        calls.append((symbol, start_date, end_date, Path(output_dir)))
        _write_minute_csv(tmp_path / "data/alpaca/TQQQ_intraday.csv")
        _write_daily_csv(tmp_path / "data/alpaca/TQQQ_daily.csv")
        return tmp_path / "data/alpaca/TQQQ_intraday.csv", tmp_path / "data/alpaca/TQQQ_daily.csv"

    monkeypatch.setattr(cli, "download_alpaca_csvs", fake_download, raising=False)
    monkeypatch.setattr(cli, "resolve_end_date", lambda _value: pd.Timestamp("2024-01-02").date(), raising=False)
    config = OrbConfig(
        start_date="2024-01-02",
        end_date="latest",
        output_dir="results/test_cli",
        active_stop_types=("HL",),
    )

    exit_code = cli.run_from_config(config, tmp_path)

    assert exit_code == 0
    assert calls == [("TQQQ", "2024-01-02", pd.Timestamp("2024-01-02").date(), tmp_path / "data/alpaca")]
    assert (tmp_path / "results/test_cli/summary_hl.csv").exists()


def test_run_from_config_reports_missing_alpaca_credentials(capsys, tmp_path: Path):
    config = OrbConfig(start_date="2024-01-02", end_date="2024-01-02", output_dir="results/test_cli")

    exit_code = cli.run_from_config(config, tmp_path)

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "APCA_API_KEY_ID" in captured.out
    assert "APCA_API_SECRET_KEY" in captured.out
