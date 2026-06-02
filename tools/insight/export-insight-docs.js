/*
  Insight Python data dictionary exporter.

  How to use:
  1. Open an Insight docs page while logged in, for example:
     https://findata-insight.htsc.com:9151/insight_help/python_dataDictionary/commonData/TradeCalendar/
  2. Open DevTools Console.
  3. Paste this whole file and press Enter.
  4. Wait for two downloads:
     - insight_python_data_dictionary_raw.json
     - insight_python_data_dictionary_combined.md

  The script only crawls same-origin pages under /insight_help/python_dataDictionary/.
*/

(async () => {
  const CONFIG = {
    rootPath: "/insight_help/python_dataDictionary/",
    maxPages: 800,
    delayMs: 120,
    fetchTimeoutMs: 25000,
    downloadJson: true,
    downloadMarkdown: true,
  };

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const normalizeUrl = (href, base = location.href) => {
    try {
      const url = new URL(href, base);
      url.hash = "";
      url.search = "";
      if (url.origin !== location.origin) return null;
      if (!url.pathname.startsWith(CONFIG.rootPath)) return null;
      if (!url.pathname.endsWith("/")) {
        const last = url.pathname.split("/").pop() || "";
        if (!last.includes(".")) url.pathname += "/";
      }
      return url.href;
    } catch {
      return null;
    }
  };

  const unique = (values) => Array.from(new Set(values.filter(Boolean)));

  const cleanText = (value) =>
    (value || "")
      .replace(/\r/g, "")
      .replace(/[ \t]+\n/g, "\n")
      .replace(/\n{4,}/g, "\n\n\n")
      .trim();

  const expandNavigation = async () => {
    const selectors = [
      "[aria-expanded='false']",
      ".sidebar button",
      ".sidebar .arrow",
      ".sidebar-heading",
      ".theme-default-sidebar button",
      ".theme-default-sidebar .arrow",
    ];

    for (let pass = 0; pass < 8; pass += 1) {
      const before = document.querySelectorAll(`a[href^='${CONFIG.rootPath}'], a[href*='${CONFIG.rootPath}']`).length;
      const candidates = unique(
        selectors.flatMap((selector) => Array.from(document.querySelectorAll(selector)))
      ).filter((el) => {
        const expanded = el.getAttribute("aria-expanded");
        const className = String(el.className || "").toLowerCase();
        return expanded === "false" || className.includes("collapsed") || className.includes("closed");
      });

      for (const el of candidates) {
        try {
          el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
        } catch {
          // Some decorative nodes are not clickable; ignore them.
        }
      }

      await sleep(80);
      const after = document.querySelectorAll(`a[href^='${CONFIG.rootPath}'], a[href*='${CONFIG.rootPath}']`).length;
      if (after <= before) break;
    }
  };

  const pickContentRoot = (doc) => {
    const selectors = [
      "main",
      "article",
      ".theme-default-content",
      ".markdown-body",
      ".content",
      ".page",
      "#app",
      "body",
    ];
    for (const selector of selectors) {
      const el = doc.querySelector(selector);
      if (el && cleanText(el.textContent).length > 80) return el.cloneNode(true);
    }
    return doc.body ? doc.body.cloneNode(true) : doc.documentElement.cloneNode(true);
  };

  const removeChrome = (root) => {
    root
      .querySelectorAll(
        [
          "script",
          "style",
          "noscript",
          "iframe",
          "svg",
          "nav",
          "aside",
          "header",
          "footer",
          ".sidebar",
          ".navbar",
          ".theme-default-sidebar",
          ".page-nav",
          ".table-of-contents",
          ".toc",
        ].join(",")
      )
      .forEach((el) => el.remove());
  };

  const extractTables = (root) =>
    Array.from(root.querySelectorAll("table")).map((table, tableIndex) => {
      const rows = Array.from(table.querySelectorAll("tr")).map((tr) =>
        Array.from(tr.querySelectorAll("th,td")).map((cell) => cleanText(cell.textContent))
      );
      return { tableIndex, rows };
    });

  const extractPage = (html, url) => {
    const doc = new DOMParser().parseFromString(html, "text/html");
    const rawTitle =
      cleanText(doc.querySelector("h1")?.textContent) ||
      cleanText(doc.querySelector("title")?.textContent) ||
      url;

    const links = unique(
      Array.from(doc.querySelectorAll("a[href]"))
        .map((a) => normalizeUrl(a.getAttribute("href"), url))
        .filter((href) => href && href !== url)
    );

    const contentRoot = pickContentRoot(doc);
    removeChrome(contentRoot);

    const headings = Array.from(contentRoot.querySelectorAll("h1,h2,h3,h4,h5,h6")).map((h) => ({
      level: Number(h.tagName.slice(1)),
      text: cleanText(h.textContent),
    }));

    const codeBlocks = Array.from(contentRoot.querySelectorAll("pre, pre code"))
      .map((el) => cleanText(el.textContent))
      .filter(Boolean);

    const tables = extractTables(contentRoot);
    const text = cleanText(contentRoot.textContent);

    return {
      url,
      title: rawTitle,
      headings,
      text,
      codeBlocks: unique(codeBlocks),
      tables,
      links,
    };
  };

  const fetchWithTimeout = async (url) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), CONFIG.fetchTimeoutMs);
    try {
      const response = await fetch(url, {
        credentials: "include",
        signal: controller.signal,
      });
      const contentType = response.headers.get("content-type") || "";
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (!contentType.includes("text/html")) {
        throw new Error(`Unexpected content-type: ${contentType || "unknown"}`);
      }
      return await response.text();
    } finally {
      clearTimeout(timer);
    }
  };

  const download = (filename, text, type) => {
    const blob = new Blob([text], { type });
    const href = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = href;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(href), 3000);
  };

  const pageToMarkdown = (page) => {
    const tableMarkdown = page.tables
      .filter((table) => table.rows.length)
      .map((table) => {
        const maxCols = Math.max(...table.rows.map((row) => row.length));
        const rows = table.rows.map((row) =>
          Array.from({ length: maxCols }, (_, i) => (row[i] || "").replace(/\|/g, "\\|"))
        );
        const header = rows[0] || [];
        const separator = Array.from({ length: maxCols }, () => "---");
        const body = rows.slice(1);
        return [header, separator, ...body].map((row) => `| ${row.join(" | ")} |`).join("\n");
      })
      .join("\n\n");

    const codeMarkdown = page.codeBlocks
      .map((code) => ["```python", code, "```"].join("\n"))
      .join("\n\n");

    return [
      `# ${page.title}`,
      "",
      `Source: ${page.url}`,
      "",
      "## Headings",
      "",
      page.headings.map((h) => `${"  ".repeat(Math.max(0, h.level - 1))}- ${h.text}`).join("\n"),
      "",
      "## Text",
      "",
      page.text,
      tableMarkdown ? "\n## Tables\n\n" + tableMarkdown : "",
      codeMarkdown ? "\n## Code Blocks\n\n" + codeMarkdown : "",
    ]
      .filter((part) => part !== "")
      .join("\n");
  };

  const startUrl = normalizeUrl(location.href);
  if (!startUrl) {
    throw new Error(`Current page must be under ${location.origin}${CONFIG.rootPath}`);
  }

  await expandNavigation();

  const queue = [startUrl];
  const seen = new Set();
  const pages = [];
  const errors = [];

  console.log("[Insight exporter] Start:", startUrl);

  while (queue.length && pages.length < CONFIG.maxPages) {
    const url = queue.shift();
    if (!url || seen.has(url)) continue;
    seen.add(url);

    try {
      console.log(`[Insight exporter] Fetching ${pages.length + 1}: ${url}`);
      const html = url === startUrl ? document.documentElement.outerHTML : await fetchWithTimeout(url);
      const page = extractPage(html, url);
      pages.push(page);

      for (const link of page.links) {
        if (!seen.has(link) && !queue.includes(link)) queue.push(link);
      }
    } catch (error) {
      console.warn("[Insight exporter] Failed:", url, error);
      errors.push({ url, error: String(error && error.message ? error.message : error) });
    }

    await sleep(CONFIG.delayMs);
  }

  const exportedAt = new Date().toISOString();
  const result = {
    exportedAt,
    source: startUrl,
    origin: location.origin,
    rootPath: CONFIG.rootPath,
    pageCount: pages.length,
    errorCount: errors.length,
    pages,
    errors,
  };

  console.log("[Insight exporter] Done:", {
    pageCount: result.pageCount,
    errorCount: result.errorCount,
    exportedAt,
  });

  if (CONFIG.downloadJson) {
    download(
      "insight_python_data_dictionary_raw.json",
      JSON.stringify(result, null, 2),
      "application/json;charset=utf-8"
    );
  }

  if (CONFIG.downloadMarkdown) {
    const markdown = [
      "# Insight Python Data Dictionary Export",
      "",
      `Exported at: ${exportedAt}`,
      `Source: ${startUrl}`,
      `Pages: ${pages.length}`,
      `Errors: ${errors.length}`,
      "",
      "## Page Index",
      "",
      ...pages.map((page, index) => `${index + 1}. [${page.title}](${page.url})`),
      "",
      "---",
      "",
      ...pages.map(pageToMarkdown),
    ].join("\n");
    download("insight_python_data_dictionary_combined.md", markdown, "text/markdown;charset=utf-8");
  }

  return result;
})();
