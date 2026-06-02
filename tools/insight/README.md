# Insight 文档导出工具

这个目录用于把已登录浏览器里的华泰 Insight Python 数据字典导出成本地文件，方便后续整理成 Markdown 或 Codex skill。

## 使用步骤

1. 用 Chrome 打开任意 Insight Python 数据字典页面，并确认已经登录。
   示例：
   `https://findata-insight.htsc.com:9151/insight_help/python_dataDictionary/commonData/TradeCalendar/`
2. 按 `F12` 打开 DevTools，进入 `Console`。
3. 打开 `tools/insight/export-insight-docs.js`，全选复制，粘贴到 Console 后回车。
4. 等待控制台输出 `[Insight exporter] Done`。
5. 浏览器会下载两个文件：
   - `insight_python_data_dictionary_raw.json`
   - `insight_python_data_dictionary_combined.md`
6. 把这两个文件移动到 `D:\quant_study\tools\insight\exports\` 或直接告诉我下载路径，我再继续整理。

## 安全边界

- 脚本只抓取当前站点同源、且路径以 `/insight_help/python_dataDictionary/` 开头的页面。
- 脚本不读取 cookie、localStorage、密码或账号信息。
- 脚本通过浏览器自己的登录态访问文档页面，等价于你手动打开这些文档页后复制正文。
- 如果网页结构变化，导出的 Markdown 可能会带上少量导航文字；后续整理阶段可以清洗。

## 下一步整理目标

拿到导出文件后，可以生成：

- `docs/insight/python_data_dictionary/index.md`
- 按数据域拆分的 reference 文档，例如 `common-data.md`、`stock-data.md`、`bond-data.md`
- 一个轻量 `insight-data` skill，让 Codex 后续知道如何查找 Insight 数据获取方法
