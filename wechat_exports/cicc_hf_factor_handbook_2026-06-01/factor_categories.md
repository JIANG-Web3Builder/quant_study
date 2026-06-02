# 高频价量因子分类与复现说明

来源：本文件由 `hfq_factor.pdf` 渲染、OCR、人工校正后整理。公式/表格以 `figures/` 中的本地图像为准，结构化字段见 `factor_specs.csv`。

## 总体回测口径

- 高频数据：Level2，包含分钟K线、3s/30s快照、逐笔成交、逐笔委托、集合竞价与盘口深度。
- 股票池：全市场、沪深300、中证500、中证1000。
- 文中主要统计区间：多数早期类别为 2013-01-14 至 2023-12-01；流动性/拥挤度/资金流/复合因子多处注明 2018-01-08 至 2023-12-01。
- 超额收益基准：有效股票池等权表现。
- 指标：IC均值、ICIR、多空年化收益、多空夏普、多头年化超额、多头超额夏普、多头超额最大回撤、多头超额胜率、换手率。
- 变体后缀：文中大量出现 `_o`、`_m`、`_std`、`_z`，应理解为同一基础因子的不同日度/截面处理版本；复现时先实现基础因子，再统一做变体处理。

## 优先复现顺序

1. `mmt_ols_beta_mean_o`：QRS/OLS beta 动量，动量反转代表。
2. `vol_upVol_std`：上行波动率，波动率代表。
3. `shape_skew_m` / `shape_skew_std`：分钟收益偏度，高阶特征代表。
4. `liq_amihud_1min_o`：分钟 Amihud 非流动性，流动性代表。
5. `corr_pvl_std` / `corr_pv_std`：量价相关性代表。
6. `doc_vol_pdf90_std` / `doc_vol_pdf95_std`：筹码分布分位因子代表。
7. `crowd_fftv20_3s_w0_std` / `crowd_fftv50m10_std`：傅里叶拥挤度代表。
8. `trade_headRatio_std` / `trade_top20retRatio_m`：资金流代表。
9. `syn_corr_o` / `syn_crowd_o` / `syn_mmt_o`：单类因子实现稳定后再做复合。

## 图像索引

- 所有 PDF 页面：`pages/page_001.png` 到 `pages/page_049.png`。
- 所有图表裁剪：`figures/figure_XX_*.png`，跨页图优先使用 `_continued.png`。
- 图表总索引：`figure_index.csv`。
- 回测图像映射：`backtest_chart_map.csv`。

## 文件使用建议

- 写代码前先读取 `factor_specs.csv`，按 `category` 和 `factor_code_base` 建函数。
- 遇到 OCR 或文字定义不清时，打开对应 `construction_figure` 或 `construction_page` 核对。
- 做回测复现时，用 `backtest_chart_map.csv` 找对应类别的 monthly/weekly backtest 和净值图。
