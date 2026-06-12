"""Crypto high-frequency factor library.

Each factor maps a single symbol's 1-minute DataFrame to a daily Series. The
``REGISTRY`` aggregates every implemented base factor; ``DIRECTIONS`` records the
economic sign used by the backtest (``-1`` reverses the factor so that a higher
adjusted value is expected to predict higher future returns).
"""

from __future__ import annotations

from . import (
    base,
    chip_dist,
    corr_factors,
    liquidity,
    momentum,
    shape,
    trade_flow,
    volatility,
)

REGISTRY: dict = {}
for _mod in (
    momentum,
    volatility,
    shape,
    liquidity,
    corr_factors,
    chip_dist,
    trade_flow,
):
    REGISTRY.update(_mod.FACTORS)

# Factor direction. The handbook describes volatility factors as
# "high volatility -> low future return", so they are reversed (-1). Amihud
# illiquidity is likewise a reversal-style factor. Everything else defaults
# to +1 and the IC sign in the report reveals the empirical direction.
DIRECTIONS: dict[str, int] = {name: 1 for name in REGISTRY}
for _name in REGISTRY:
    if _name.startswith("vol_"):
        DIRECTIONS[_name] = -1
DIRECTIONS["liq_amihud_1min"] = -1

TOP_PRIORITY = [
    "mmt_ols_beta_mean",
    "vol_upVol",
    "shape_skew",
    "liq_amihud_1min",
    "corr_pv",
    "corr_pvl",
    "doc_vol_pdf90",
    "doc_vol_pdf95",
    "trade_headRatio",
    "trade_top20retRatio",
]

__all__ = ["REGISTRY", "DIRECTIONS", "TOP_PRIORITY", "base"]
