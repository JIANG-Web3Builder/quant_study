ORB Strategy 本地落地计划
Summary
在 D:\quant_study\ORB_strategy 下建立一个可运行、可测试、可后续接 API 数据的 Python 回测工程，复现 PDF 中的 “Backtesting the ORB Strategy with Free Alpaca Data”。默认策略口径锁定为：TQQQ、1 分钟日内 bar、日线 ATR%、5 分钟 opening range、同时跑 H/L 与 ATR 两种止损模式、无盈利目标、按账户权益固定风险比例开仓，并输出权益曲线、绩效汇总、月度收益表。

Key Changes
新建本地包 orb_backtest，核心模块包括配置、数据读取、交易日过滤、ATR 指标、ORB 回测引擎、绩效指标、绘图和 CLI。
使用 configs/orb_tqqq.yaml 固化默认参数：ticker=TQQQ、start_date=2016-01-01、end_date=2026-04-20、orb_minutes=5、risk=0.01、max_leverage=4、initial_capital=25000、commission=0.0005、atr_period=14、stop_atr=0.05。
数据入口先兼容本地 CSV：data/alpaca/{TICKER}_intraday.csv 与 data/alpaca/{TICKER}_daily.csv；后续拿到 API 后只需要补 downloader/adapter，不改回测核心。
回测行为按 PDF 修正并本地化：先标准化分钟线字段和纽约时区；日线计算 ATR(14) / daily_open 并滞后一日；用 NYSE 日历过滤早收盘日真实收盘后的 bar；第 N 根决定多空，第 N+1 根开盘进场。
输出写入 results/orb_tqqq/：逐日权益 CSV、绩效 summary CSV/Markdown、月度收益 CSV/Markdown、权益曲线 PNG。
附带 README，说明数据字段要求、API 数据下载后的放置路径、运行命令和结果解释。
Public Interfaces
CLI 命令：
python -m orb_backtest.cli --config configs/orb_tqqq.yaml
本地数据字段约定：
intraday CSV 至少包含：datetime_et 或 caldt、open、high、low、close、volume
daily CSV 至少包含：day、open、high、low、close
Python API：
load_intraday_bars(path, ticker)
load_daily_bars(path)
compute_atr_pct_lookup(daily_df, period=14)
run_orb_backtest(intraday_df, config, stop_type, atr_lookup=None)
summarize_performance(equity_df)
monthly_return_table(equity_df)
Test Plan
用小型人工分钟线测试方向判断：第 5 根 close 高于第 1 根 open 做多，低于则做空，相等跳过。
测试进场口径：固定在第 orb_minutes + 1 根 open 进场。
测试 H/L 止损：多头用 opening range low，空头用 opening range high。
测试 ATR 止损：使用前一交易日 ATR(14)/daily_open 查表，缺失时跳过当日交易。
测试仓位：floor(previous_AUM * risk / (entry * stop_distance))，并受 max_leverage * AUM / entry 限制。
测试绩效指标：total return、CAGR、volatility、Sharpe、max drawdown、月度收益表。
运行验证命令：python -m pytest；若无真实数据，CLI 应给出清晰的缺数据提示而不是崩溃。
Assumptions
第一版不主动调用 Alpaca API，只预留 adapter 边界；你拿到 API 并下载数据后即可回测。
默认复现 PDF 的 Alpaca 口径：日内分钟线不复权，日线使用复权后 OHLC 来计算 ATR%。
PDF 中原 notebook 的 TICKER 未定义错误会在本地实现中修正为配置驱动。
早收盘过滤依赖 exchange_calendars；若本地环境未安装，实现时加入依赖说明或 requirements。
第一版聚焦单标的 ORB 复现，不扩展到多标的组合、参数网格搜索或实盘交易。