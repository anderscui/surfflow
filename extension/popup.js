async function getCurrentPageContext() {
  const [tab] = await browser.tabs.query({
    active: true,
    currentWindow: true,
  });

  if (!tab?.id) {
    throw new Error("No active tab found.");
  }

  const results = await browser.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => window.getSelection().toString()
  });

  // if (!results.length) {
  //   return {
  //     text: "",
  //     url: tab.url ?? "",
  //     title: tab.title ?? "",
  //   }
  // }

  const selectedText = results[0]?.result ?? "";

  return {
    text: selectedText,
    url: tab.url || "",
    title: tab.title || "",
  };
}

function waitForTabComplete(tabId) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      browser.tabs.onUpdated.removeListener(listener);
      reject(new Error("Douban search page loading timeout."));
    }, 15000);

    function listener(updatedTabId, changeInfo, tab) {
      if (updatedTabId === tabId && changeInfo.status === "complete") {
        clearTimeout(timeout);
        browser.tabs.onUpdated.removeListener(listener);
        resolve(tab);
      }
    }

    browser.tabs.onUpdated.addListener(listener);
  });
}

async function getRecentHistory() {
  const oneDayAgo = Date.now() - (24 * 60 * 60 * 1000); // 24小时前的时间戳

  const historyItems = await browser.history.search({
    text: "",                // 空字符串代表搜所有网址
    startTime: oneDayAgo,    // 开始时间
    maxResults: 100          // 最多拿 100 条
  });

  historyItems.forEach(item => {
    console.log(`History: ${item.title} 🔗 ${item.url} (Visit Count: ${item.visitCount})`);
  });

  return historyItems;
}

function buildDoubanSearchUrl(text, type) {
  const encoded = encodeURIComponent(text.trim());

  if (type === "book") {
    return `https://search.douban.com/book/subject_search?search_text=${encoded}&cat=1001`;
  }

  if (type === "movie") {
    return `https://search.douban.com/movie/subject_search?search_text=${encoded}&cat=1002`;
  }

  throw new Error(`Unsupported search type: ${type}`);
}

document.getElementById("showSelected").addEventListener("click", async () => {
  let context = await getCurrentPageContext();
  let selectedText = context.text || "No text selected.";

  console.log(selectedText);
  alert(selectedText);

  // const q = encodeURIComponent(selectedText);
  // browser.tabs.create({
  //   url: `http://www.douban.com/search?q=${q}`
  // });
});

document.getElementById("showHistory").addEventListener("click", async () => {
  // console.log("正在尝试捞取过去 24 小时历史记录...");
  const history = await getRecentHistory();
  console.log(`成功捞取到 ${history.length} 条历史数据。`);
});

async function extractBooks() {
  const resultEl = document.getElementById("result");
  resultEl.textContent = "Extracting...";

  try {
    const { text, url, title } = await getCurrentPageContext();

    if (!text.trim()) {
      resultEl.textContent = "No selected text.";
      return;
    }

    const resp = await fetch("http://127.0.0.1:8000/api/v1/extract/books", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        url,
        title,
      }),
    });

    if (!resp.ok) {
      const errorText = await resp.text();
      resultEl.textContent = `Error ${resp.status}: ${errorText}`;
      return;
    }

    const data = await resp.json();

    if (!data.books || data.books.length === 0) {
      resultEl.textContent = "No book titles found.";
      return;
    }

    resultEl.textContent = data.books.join("\n");
  } catch (err) {
    resultEl.textContent = `Failed: ${err.message}`;
  }
}

function extractDoubanSearchResultsFromPage() {
  function clean(text) {
    return (text || "").replace(/\s+/g, " ").trim();
  }

  function extractFromSearchDouban() {
    const items = Array.from(document.querySelectorAll(".item-root"));

    return items.slice(0, 5).map((item) => {
      const linkEl =
        item.querySelector("a.title-text") ||
        item.querySelector(".title a") ||
        item.querySelector("a[href*='subject']");

      const imgEl = item.querySelector("img");
      const ratingEl =
        item.querySelector(".rating_nums") ||
        item.querySelector(".rating span") ||
        item.querySelector("[class*='rating']");

      const metaEl =
        item.querySelector(".meta") ||
        item.querySelector(".abstract") ||
        item.querySelector(".detail");

      return {
        title: clean(linkEl?.textContent),
        url: linkEl?.href || "",
        cover: imgEl?.src || "",
        rating: clean(ratingEl?.textContent),
        meta: clean(metaEl?.textContent),
      };
    }).filter(item => item.title || item.url);
  }

  function extractFromWwwDouban() {
    const items = Array.from(document.querySelectorAll(".result"));

    return items.slice(0, 5).map((item) => {
      const linkEl =
        item.querySelector(".title h3 a") ||
        item.querySelector(".content .title a") ||
        item.querySelector("a[href*='subject']");

      const imgEl = item.querySelector("img");
      const contentEl = item.querySelector(".content");

      return {
        title: clean(linkEl?.textContent),
        url: linkEl?.href || "",
        cover: imgEl?.src || "",
        rating: "",
        meta: clean(contentEl?.textContent),
      };
    }).filter(item => item.title || item.url);
  }

  const results = extractFromSearchDouban();
  console.log(results);

  if (results.length > 0) {
    return results;
  }

  return extractFromWwwDouban();
}

async function searchDouban(type) {
  const resultEl = document.getElementById("result");
  resultEl.textContent = "Searching...";

  let tab = null;

  try {
    const page = await getCurrentPageContext();
    const text = page.text.trim();

    if (!text) {
      resultEl.textContent = "No text selected.";
      return;
    }

    const searchUrl = buildDoubanSearchUrl(text, type);
    console.log(`search URL: ${searchUrl}`);

    // const hasPermission = await browser.permissions.contains({
    //   origins: ["*://*.douban.com/*"],
    // });
    // console.log("has douban permission:", hasPermission);

    tab = await browser.tabs.create({
      url: searchUrl,
      active: false,
    });

    await waitForTabComplete(tab.id);

    // 豆瓣搜索页有时会继续异步渲染，稍微等一下。
    await new Promise(resolve => setTimeout(resolve, 1500));

    const injected = await browser.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractDoubanSearchResultsFromPage,
    });

    const items = injected[0]?.result ?? [];

    resultEl.textContent = JSON.stringify(
      {
        query: text,
        type,
        items,
      },
      null,
      2,
    );
  } catch (err) {
    resultEl.textContent = `Failed: ${err.message}`;
  } finally {
    if (tab?.id) {
      await browser.tabs.remove(tab.id).catch(() => {});
    }
  }
}

document.getElementById("extractBooks").addEventListener("click", extractBooks);

document.getElementById("searchBooks").addEventListener("click", () => {
  searchDouban("book");
});

document.getElementById("searchMovies").addEventListener("click", () => {
  searchDouban("movie");
});
