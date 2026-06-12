# Crypto Replication — CICC 高频价量因子在加密市场的复现

本子项目将 CICC《高频价量因子手册》(`../hfq_factor.pdf`,
结构化字段见 `../factor_specs.json`) 中的核心日内高频因子，迁移到加密货币
现货市场（Binance 1 分钟 K 线），并提供完整的 IC 分析与多空回测流程。

## 目录结构

```
crypto_replication/
  requirements.txt
  README.md
  data/
    __init__.py
    binance_downloader.py   # Binance 公开 REST API 1m K线下载
  factors/
    __init__.py             # 因子注册表 REGISTRY / 方向 DIRECTIONS
    base.py                 # 变体处理 (_o/_m/_std/_z) + 日度聚合工具
    momentum.py             # 动量反转
    volatility.py           # 波动率
    shape.py                # 高阶特征 (偏度/峰度)
    liquidity.py            # 流动性 (Amihud 等)
    corr_factors.py         # 量价相关性
    chip_dist.py            # 筹码分布 (成交量加权收益分布)
    trade_flow.py           # 资金流 (开盘/尾盘/高收益成交占比)
  backtest/
    __init__.py
    ic_analysis.py          # 截面 Spearman IC、ICIR、胜率
    long_short.py           # 多空分组回测 (年化/夏普/最大回撤)
    report.py               # 汇总表 + 净值/IC 曲线
  main.py                   # 主流程 CLI
```

## 安装

```bash
pip install -r requirements.txt
```

> 说明：`pyarrow` 用于读写 parquet（`pandas.to_parquet` / `read_parquet` 的引擎），
> 因此在题面给出的 6 个依赖基础上额外加入。

## 快速开始

```bash
# 默认：自动取 Binance 现货成交额前 50 的 USDT 交易对，下载最近 90 天 1m 数据，
# 月度频率回测全部因子
python main.py --freq monthly

# 指定交易对与因子
python main.py --symbols BTCUSDT ETHUSDT SOLUSDT \
               --factors mmt_ols_beta_mean vol_upVol shape_skew \
               --freq weekly

# 指定日期范围
python main.py --start 2024-01-01 --end 2024-04-01

# 已经下载过数据后，仅跑回测（不再访问 API）
python main.py --skip-download
```

CLI 参数：

| 参数 | 说明 |
| --- | --- |
| `--symbols` | 交易对列表（默认自动取前 50） |
| `--start` / `--end` | 日期范围（缺省用 `--days` 回看） |
| `--days` | 缺省回看天数（默认 90） |
| `--factors` | 指定基础因子（默认全部） |
| `--freq` | `weekly` 或 `monthly` |
| `--top-n` | 自动选币数量（默认 50） |
| `--skip-download` | 复用已保存 parquet，不访问 API |

输出写入 `crypto_replication/results/`：

- `factor_summary.csv`：每个因子变体的 IC 均值、ICIR、胜率、多空年化/夏普/最大回撤
- `long_short_equity_curves.png`：多空净值曲线
- `cumulative_ic.png`：累计 IC 曲线

## 口径与约定

- **"日"的定义**：加密市场 24h 连续交易，统一以 UTC 00:00:00–23:59:00（1440 根 1m K 线）为一个交易日。
- **数据质量过滤**：当日 K 线数量不足 100 根的 (symbol, 日期) 被剔除，避免缺失数据噪声。
- **Amihud**：用 `quote_volume`（USDT 成交额）替代 A 股成交额，
  `illiq_i = |ret_i| / quote_volume_i`，过滤 `quote_volume == 0` 的 K 线。
- **变体后缀**（`factors/base.py`）：
  - `_o`：当日原始日度值
  - `_m`：过去 20 个交易日滚动均值
  - `_std`：过去 20 个交易日滚动标准化 `(x - mean) / std`
  - `_z`：同一日期对所有 symbol 的截面 z-score
- **因子方向**：参考手册 notes。波动率类因子（`vol_*`）与 Amihud 非流动性
  （`liq_amihud_1min`）描述为"高波动/高非流动性 → 低未来收益"，回测中方向取负
  （见 `factors/__init__.py` 的 `DIRECTIONS`）；其余因子默认正向，由 IC 符号反映经验方向。

## 已实现因子

| 类别 | 因子 |
| --- | --- |
| 动量反转 | `mmt_ols_beta_mean`★, `mmt_last30`, `mmt_am`, `mmt_pm`, `mmt_top20VolumeRet` |
| 波动率 | `vol_return1min`, `vol_upVol`★, `vol_downVol`, `vol_upRatio`, `vol_downRatio`, `vol_range1min`, `vol_volume1min` |
| 高阶特征 | `shape_skew`★, `shape_kurt`, `shape_skratio`, `shape_skewVol`, `shape_kurtVol`, `shape_skratioVol` |
| 流动性 | `liq_amihud_1min`★, `liq_closevol` |
| 量价相关性 | `corr_pv`★, `corr_pvl`★, `corr_pvd`, `corr_prv`, `corr_prvr`, `corr_pvr` |
| 筹码分布 | `doc_vol_pdf90`★, `doc_vol_pdf95`★, `doc_vol_pdf90bi`, `doc_skew`, `doc_kurt`, `doc_vol10_ratio` |
| 资金流 | `trade_headRatio`★, `trade_tailRatio`, `trade_top20retRatio`★, `trade_bottom20retRatio`, `trade_top50retRatio` |

★ = 手册中标注的优先复现因子。每个基础因子自动派生 4 个变体（`_o/_m/_std/_z`）。

## 跳过的因子（数据不可得）

加密公开 K 线无法提供 tick / 盘口深度 / 逐笔成交 / 集合竞价数据，因此以下手册因子
在本项目中**跳过**：

- 拥挤度傅里叶类：`crowd_fftv*`（需 3s/30s 快照成交量序列）
- 流动性：`liq_spread`（买卖价差）、`liq_firstCallR` / `liq_lastCallR`（集合竞价量占比）、
  深度类 `liq_*DepthCct`
- 资金流：`trade_bidAskRatio`（盘口）、`trade_CBuyRatio` / `trade_CSellRatio` /
  `trade_netBuyRatio`（主动买卖逐笔分类）
- 复合因子 `syn_*`：依赖上述被跳过的单类因子，故一并跳过

## 模块说明

- `data/binance_downloader.py`
  - `get_top_usdt_symbols(top_n)`：按 24h 成交额筛选 USDT 现货前 N（剔除杠杆代币）
  - `download_klines(symbol, start, end)`：分页拉取 1m K 线
  - `download_symbols(symbols, start, end, save_dir)`：批量下载并存 `data/raw/*.parquet`
  - `load_minute_data(symbol, data_dir)`：读取并按 `open_time` 建索引
- `factors/base.py`：`apply_variants`、`cross_sectional_zscore`、`variant_panels`、
  `daily_apply`（按 UTC 日分组聚合 + 最少 K 线过滤）
- `backtest/ic_analysis.py`：`select_rebalance_dates`、`period_forward_returns`、`compute_ic`
- `backtest/long_short.py`：`run_long_short`（多头 top 20% / 空头 bottom 20%）
- `backtest/report.py`：`generate_report`（汇总 CSV + matplotlib 图）
```
