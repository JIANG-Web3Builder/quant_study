#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Save local Insight credentials for the demo runner."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess


CONFIG_PATH = pathlib.Path(__file__).with_name("insight_local_config.json")


def _encrypt_windows_dpapi(password: str) -> str:
    if os.name != "nt":
        raise RuntimeError("This helper currently stores passwords with Windows DPAPI only.")

    script = f"""
$ErrorActionPreference = 'Stop'
$secure = ConvertTo-SecureString -String @'
{password}
'@ -AsPlainText -Force
[Console]::Out.Write(($secure | ConvertFrom-SecureString))
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Failed to encrypt Insight password.")
    return completed.stdout.strip()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Save ignored local Insight login config.")
    parser.add_argument("--user", default=os.environ.get("INSIGHT_USER"), help="Insight account name.")
    parser.add_argument("--password", default=os.environ.get("INSIGHT_PASSWORD"), help="Insight account password.")
    parser.add_argument("--mode", default=os.environ.get("INSIGHT_LOGIN_MODE", "uat"), choices=["prod", "uat", "sit"])
    parser.add_argument("--ip", default=os.environ.get("INSIGHT_IP", "221.6.6.131"))
    parser.add_argument("--port", default=int(os.environ.get("INSIGHT_PORT", "9242")), type=int)
    args = parser.parse_args(argv)

    if not args.user or not args.password:
        raise SystemExit("Provide --user/--password or set INSIGHT_USER/INSIGHT_PASSWORD.")

    payload = {
        "user": args.user,
        "password_dpapi": _encrypt_windows_dpapi(args.password),
        "login_mode": args.mode,
        "ip": args.ip,
        "port": args.port,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "note": "password_dpapi is encrypted for the current Windows user and machine.",
    }
    CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved Insight config to {CONFIG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
