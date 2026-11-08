import { parseLatestPage } from './latest-parser.js';

const BASE_URL = 'https://book.douban.com/latest';
const API_BASE = 'http://127.0.0.1:8000/api/v1/douban/book_latest';
const API_KEY = 'a-random-secret'; // Replace with your configured SURFFLOW_API_KEY.
const MAX_PAGES = 20;
const PAUSE_MS = 400;
let running = false;

function buildPageUrl(page) {
  const url = new URL(BASE_URL);
  url.searchParams.set('subcat', '全部');
  url.searchParams.set('p', String(page));
  url.searchParams.set('updated_at', '');
  return url.href;
}

async function fetchPage(page) {
  const url = buildPageUrl(page);
  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) throw new Error(`豆瓣 HTTP ${response.status}：${url}`);
  const parsed = parseLatestPage(await response.text(), response.url);
  if (parsed.page_number !== page) {
    throw new Error(`请求第 ${page} 页，却得到第 ${parsed.page_number} 页，取消同步`);
  }
  return parsed;
}

async function saveBatch(books, pagesRead) {
  const response = await fetch(`${API_BASE}/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
    body: JSON.stringify({
      source_url: buildPageUrl(1),
      pages_read: pagesRead,
      books,
    }),
  });
  if (!response.ok) throw new Error(`FastAPI HTTP ${response.status}：${await response.text()}`);
  return response.json();
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export async function syncLatestBooks() {
  const byId = new Map();
  let pagesRead = 0;
  let maxPages = MAX_PAGES;

  for (let page = 1; page <= maxPages; page++) {
    if (page > 1) await sleep(PAUSE_MS);
    const parsed = await fetchPage(page);
    pagesRead++;
    for (const book of parsed.books) {
      if (!byId.has(book.id)) byId.set(book.id, book);
    }
    console.log(`Douban latest: page ${page}, found ${parsed.books.length}, unique ${byId.size}`);

    // Pagination exposes the total number of pages; clamp the scan to 20.
    if (page === 1) maxPages = Math.min(MAX_PAGES, parsed.max_linked_page);
    if (!parsed.has_next) break;
  }
  if (!byId.size) throw new Error('没有解析到图书，未写入数据库');
  return saveBatch([...byId.values()], pagesRead);
}

export function initDoubanLatest() {
  // Register synchronously during background initialization.
  browser.runtime.onMessage.addListener(message => {
    if (message?.type !== 'douban-book-latest-sync') return undefined;
    if (running) return Promise.resolve({ status: 'running', message: '新书速递正在同步' });
    running = true;
    return syncLatestBooks()
      .catch(error => ({ status: 'error', message: String(error?.message || error) }))
      .finally(() => { running = false; });
  });
}
