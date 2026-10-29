import {logOperation} from "./api.js";

browser.runtime.onInstalled.addListener(() => {
  const items = [
    ["douban_book", "Search Douban Books"],
    ["douban_movie", "Search Douban Movies"],
    ["amazon_book", "Search Amazon Books"],
    ["zlib", "Search Z-Library"],
    ["wikipedia", "Search Wikipedia"],
    ["goodreads", "Search Goodreads"],
    ["arxiv", "Search arXiv"],
    ["semantic_scholar", "Search Semantic Scholar"],
    ["alphaxiv", "Search alphaXiv"],
    ["github_repo", "Search GitHub Repo"],
    ["github_code", "Search GitHub Code"],
  ];

  for (const [id, title] of items) {
    browser.menus.create({
      id,
      title: `${title}: "%s"`,
      contexts: ["selection"],
    });
  }
});

browser.menus.onClicked.addListener(async (info, tab) => {
  const rawQuery = info.selectionText || "";
  const query = cleanSelectedText(rawQuery);

  if (!query) return;

  const targetUrl = buildContextSearchUrl(info.menuItemId, query);
  if (!targetUrl) return;

  await browser.tabs.create({
    url: targetUrl,
    active: false,
    index: tab.index + 1,
  });

  await logOperation({
    action: "context_menu_search",
    pageUrl: tab?.url ?? "",
    pageTitle: tab?.title ?? "",
    context: {
      provider: info.menuItemId,
      raw_query: rawQuery,
      query,
      target_url: targetUrl,
    },
  }).catch(err => {
    console.warn("logOperation failed:", err);
  });
});

function cleanSelectedText(text) {
  return (text || "")
    .replace(/<[^>]+>/g, " ")       // 去掉明显 HTML tag
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}

function buildContextSearchUrl(site, query) {
  const q = encodeURIComponent(query.trim());

  const urls = {
    douban_book: `https://search.douban.com/book/subject_search?search_text=${q}&cat=1001`,
    douban_movie: `https://search.douban.com/movie/subject_search?search_text=${q}&cat=1002`,
    amazon_book: `https://www.amazon.com/s?k=${q}&i=stripbooks`,
    zlib: `https://1lib.sk/s/?q=${q}`,
    wikipedia: `https://en.wikipedia.org/w/index.php?search=${q}`,
    goodreads: `https://www.goodreads.com/search?q=${q}`,
    arxiv: `https://arxiv.org/search/?searchtype=all&query=${q}&abstracts=show&size=50&order=`,
    semantic_scholar: `https://www.semanticscholar.org/search?q=${q}&sort=relevance`,
    alphaxiv: `https://www.alphaxiv.org/?query=${q}`,
    github_repo: `https://github.com/search?q=${q}&type=repositories`,
    github_code: `https://github.com/search?q=${q}&type=code`,
  };

  return urls[site];
}
