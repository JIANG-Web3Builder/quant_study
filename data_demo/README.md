# Insight 可用行情接口测试

这个目录只保留当前账号已经验证可用的 Insight 行情接口示例：实时订阅、行情回放，以及网页文档里额外补充且能订阅成功的接口。此前失败的 `query.get_*` 同步查询示例已经从默认测试集合移除，避免后续误以为这些接口可用。

## 一次性保存登录配置

首次使用时运行：

```powershell
.\.venv\Scripts\python.exe data_demo/save_insight_credentials.py
```

脚本会优先读取这些环境变量：

```powershell
$env:INSIGHT_USER="你的账号"
$env:INSIGHT_PASSWORD="你的密码"
$env:INSIGHT_LOGIN_MODE="uat"
$env:INSIGHT_IP="221.6.6.131"
$env:INSIGHT_PORT="9242"
```

配置会保存到 `data_demo/insight_local_config.json`，该文件已被 `.gitignore` 忽略。密码不是明文保存，而是用当前 Windows 用户的 DPAPI 加密；换机器或换 Windows 用户后需要重新保存一次。

保存后，后续运行 demo 不需要再手工输入账号、密码、网关。

## 默认环境

当前已验证的登录方式：

```text
login_mode = uat
ip         = 221.6.6.131
port       = 9242
```

如果临时要覆盖本地配置，仍然可以设置 `INSIGHT_*` 环境变量，环境变量优先级高于本地配置文件。

## 查看会运行哪些接口

```powershell
.\.venv\Scripts\python.exe data_demo/run_all_insight_demos.py --dry-run
```

默认分类：

```text
subscribe
playback
doc_extra
```

## 运行所有已验证接口

```powershell
.\.venv\Scripts\python.exe data_demo/run_all_insight_demos.py --timeout 90
```

为了少登录几次，可以使用：

```powershell
.\.venv\Scripts\python.exe data_demo/run_all_insight_demos.py --reuse-login --wait-after 3
```

## 运行单个接口

```powershell
.\.venv\Scripts\python.exe data_demo/run_all_insight_demos.py --one subscribe:subscribe_tick_by_id_demo --timeout 90
.\.venv\Scripts\python.exe data_demo/run_all_insight_demos.py --one playback:playback_tick_demo --timeout 90
.\.venv\Scripts\python.exe data_demo/run_all_insight_demos.py --one doc_extra:subscribe_future_kline_by_type_demo --timeout 90
```

## 当前保留的接口

实时订阅：

- `subscribe_tick_by_type_demo`
- `subscribe_kline_by_type_demo`
- `subscribe_trans_and_order_by_type_demo`
- `subscribe_tick_by_id_demo`
- `subscribe_kline_by_id_demo`
- `subscribe_trans_and_order_by_id_demo`
- `subscribe_derived_demo`

行情回放：

- `playback_tick_demo`
- `playback_trans_and_order_demo`

网页额外补充且订阅成功：

- `subscribe_htsc_margin_by_id_demo`
- `subscribe_htsc_margin_by_type_demo`
- `subscribe_news_by_id_demo`
- `subscribe_news_by_type_demo`
- `subscribe_future_kline_by_type_demo`

## 当前不可用的接口范围

当前账号下，大部分 `query.get_*` 同步查询接口会返回 `invalid data` 或空结果，包括但不限于：

- `query.get_kline`
- `query.get_trading_days`
- 基础资料、财务数据、公告研报、交易日历、复权因子等同步查询接口

这些接口不是 Python 调用方式的问题，而是同步查询通道或账号权限问题。后续如果华泰开通同步查询权限，可以重新从网页导出的文档里恢复这些示例。

## 报告位置

每次运行会生成 JSON 报告：

```text
data_demo/reports/
```
