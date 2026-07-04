function hasChineseText(text) {
  return /[\u4e00-\u9fff]/.test(text);
}

function buildDoubanSearchUrl(query, type) {
  const encoded = encodeURIComponent(query.trim());

  if (type === "book") {
    return `https://search.douban.com/book/subject_search?search_text=${encoded}&cat=1001`;
  }

  if (type === "movie") {
    return `https://search.douban.com/movie/subject_search?search_text=${encoded}&cat=1002`;
  }

  throw new Error(`Unsupported douban search type: ${type}`);
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

function extractDoubanSearchResultsFromPage() {
  function clean(text) {
    return (text || "").replace(/\s+/g, " ").trim();
  }

  const items = Array.from(document.querySelectorAll(".item-root"));

  return items.slice(0, 5).map((item) => {
    const linkEl =
      item.querySelector("a.title-text") ||
      item.querySelector(".title a") ||
      item.querySelector("a[href*='subject']");

    const ratingEl =
      item.querySelector(".rating_nums") ||
      item.querySelector(".rating span") ||
      item.querySelector("[class*='rating']");

    const metaEl =
      item.querySelector(".meta") ||
      item.querySelector(".abstract") ||
      item.querySelector(".detail");

    return {
      source: "douban",
      title: clean(linkEl?.textContent),
      url: linkEl?.href || "",
      rating: clean(ratingEl?.textContent),
      meta: clean(metaEl?.textContent),
    };
  }).filter(item => item.title || item.url);
}

async function searchDouban(query, type) {
  let tab = null;

  try {
    const searchUrl = buildDoubanSearchUrl(query, type);

    tab = await browser.tabs.create({
      url: searchUrl,
      active: false,
    });

    await waitForTabComplete(tab.id);

    // 豆瓣搜索页会异步渲染，稍等一下。
    await new Promise(resolve => setTimeout(resolve, 1500));

    const injected = await browser.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractDoubanSearchResultsFromPage,
    });

    return injected[0]?.result ?? [];
  } finally {
    if (tab?.id) {
      await browser.tabs.remove(tab.id).catch(() => {});
    }
  }
}
