import {waitForTabComplete} from "../commons/tabs.js";

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

function extractDoubanSearchResultsFromPage() {
  function clean(text) {
    return (text || "").replace(/\s+/g, " ").trim();
  }

  function cleanRatingCount(text) {
    return clean(text).replace(/[()]/g, "");
  }

  function parseRatingCount(text) {
    const m = clean(text).match(/(\d+)/);
    return m ? Number(m[1]) : null;
  }

  function inferDoubanItemType(url) {
    if (!url) return "unknown";

    if (url.includes("book.douban.com/series/")) return "book_series";
    if (url.includes("book.douban.com/subject/")) return "book";
    if (url.includes("book.douban.com/author/")) return "author";

    if (url.includes("movie.douban.com/subject/")) return "movie";
    if (url.includes("movie.douban.com/celebrity/")) return "celebrity";

    return "unknown";
  }

  function extractLabels(item) {
    return Array.from(item.querySelectorAll(".label"))
      .map(el => el.textContent.replace(/[\[\]]/g, "").trim())
      .filter(Boolean);
  }

  const items = Array.from(document.querySelectorAll(".item-root"));

  return items.slice(0, 5).map((item) => {
    const linkEl = item.querySelector(".title a");
    const ratingEl = item.querySelector(".rating_nums");
    const ratingCountEl = item.querySelector(".pl");
    const metaEl = item.querySelector(".meta.abstract");
    const statusEl = item.querySelector(".status-text");

    const url = linkEl?.href || "";

    return {
      source: "douban",
      title: clean(linkEl?.textContent),
      url: url,
      item_type: inferDoubanItemType(url),
      rating: clean(ratingEl?.textContent),
      rating_count: parseRatingCount(ratingCountEl?.textContent),
      rating_count_text: cleanRatingCount(ratingCountEl?.textContent),
      meta: clean(metaEl?.textContent),
      status: clean(statusEl?.textContent),
      labels: extractLabels(item),
    };
  }).filter(item => item.title || item.url);
}

export async function searchDouban(query, type) {
  let tab = null;
  console.log(`search douban...`);
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
      target: {tabId: tab.id},
      func: extractDoubanSearchResultsFromPage,
    });

    return injected[0]?.result ?? [];
  } finally {
    if (tab?.id) {
      await browser.tabs.remove(tab.id).catch(() => {
      });
    }
  }
}
