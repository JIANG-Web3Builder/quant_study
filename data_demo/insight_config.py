#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Insight login configuration.

The checked-in code reads credentials from either environment variables or the
ignored local file ``insight_local_config.json``. The helper script
``save_insight_credentials.py`` writes that local file and stores the password
with Windows DPAPI rather than plain text.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Optional


CONFIG_PATH = pathlib.Path(__file__).with_name("insight_local_config.json")

DEFAULTS: Dict[str, Any] = {
    "login_mode": "uat",
    "ip": "221.6.6.131",
    "port": 9242,
}


@dataclass(frozen=True)
class InsightConfig:
    user: str
    password: str
    login_mode: str = "uat"
    ip: str = "221.6.6.131"
    port: int = 9242


def _read_local_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _decrypt_windows_dpapi(encrypted_password: str) -> str:
    if os.name != "nt":
        raise RuntimeError("password_dpapi can only be decrypted on Windows.")

    script = f"""
$ErrorActionPreference = 'Stop'
$secure = ConvertTo-SecureString -String @'
{encrypted_password}
'@
$cred = [System.Net.NetworkCredential]::new('', $secure)
[Console]::Out.Write($cred.Password)
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Failed to decrypt Insight password.")
    return completed.stdout


def load_config(require_credentials: bool = True) -> InsightConfig:
    data: Dict[str, Any] = dict(DEFAULTS)
    data.update(_read_local_config())

    user = os.environ.get("INSIGHT_USER") or data.get("user") or data.get("username")
    password = os.environ.get("INSIGHT_PASSWORD") or data.get("password")
    encrypted_password = os.environ.get("INSIGHT_PASSWORD_DPAPI") or data.get("password_dpapi")

    if not password and encrypted_password:
        password = _decrypt_windows_dpapi(str(encrypted_password))

    login_mode = os.environ.get("INSIGHT_LOGIN_MODE") or data.get("login_mode") or DEFAULTS["login_mode"]
    ip = os.environ.get("INSIGHT_IP") or data.get("ip") or DEFAULTS["ip"]
    port = int(os.environ.get("INSIGHT_PORT") or data.get("port") or DEFAULTS["port"])

    if require_credentials and (not user or not password):
        raise RuntimeError(
            "Insight credentials are missing. Run "
            "`python data_demo/save_insight_credentials.py` once, or set "
            "INSIGHT_USER and INSIGHT_PASSWORD."
        )

    return InsightConfig(
        user=str(user or ""),
        password=str(password or ""),
        login_mode=str(login_mode).strip().lower(),
        ip=str(ip),
        port=port,
    )


def login(markets, common_module=None, login_log: bool = False) -> str:
    from insight_python.com.insight import common as default_common

    common = common_module or default_common
    cfg = load_config(require_credentials=True)
    login_functions = {
        "prod": common.login,
        "uat": common.loginUAT,
        "sit": common.loginSIT,
    }
    if cfg.login_mode not in login_functions:
        raise RuntimeError("INSIGHT_LOGIN_MODE must be one of: prod, uat, sit.")

    return login_functions[cfg.login_mode](
        markets,
        cfg.user,
        cfg.password,
        login_log=login_log,
        IP=cfg.ip,
        Port=cfg.port,
    )


def redact(text: str) -> str:
    redacted = text or ""
    secret_values = [
        os.environ.get("INSIGHT_USER"),
        os.environ.get("INSIGHT_PASSWORD"),
    ]
    try:
        data = _read_local_config()
        secret_values.extend([data.get("user"), data.get("username"), data.get("password")])
    except Exception:
        pass

    for value in secret_values:
        if value:
            redacted = redacted.replace(str(value), "<INSIGHT_SECRET>")
    return redacted
