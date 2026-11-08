import { parseChartPage } from './chart-parser.js';

const CHART_URL = 'https://book.douban.com/chart?subcat=all';
const API_URL = 'http://127.0.0.1:8000/api/v1/douban/book_chart';
const API_KEY = 'a-random-secret'; // 与现有 FastAPI 密钥保持一致
const MAX_PAGES = 5;
let running = false;

async function getJson(url) {
  const response = await fetch(url, { headers: { 'X-API-Key': API_KEY } });
  if (!response.ok) throw new Error(`API ${response.status}: ${await response.text()}`);
  return response.json();
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error(`API ${response.status}: ${await response.text()}`);
  return response.json();
}

async function fetchChart(url) {
  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) throw new Error(`豆瓣 ${response.status}: ${url}`);
  const obj = parseChartPage(await response.text(), response.url);
  // console.log(JSON.stringify(obj));
  return obj;
}

function buildPageUrl(page, updatedAt) {
  const url = new URL(CHART_URL);
  if (page > 1) url.searchParams.set('p', String(page));
  if (updatedAt) url.searchParams.set('updated_at', updatedAt);
  console.log(url.href);
  return url.href;
}

async function runChartSync() {
  const first = await fetchChart(CHART_URL);
  if (first.books.length === 0) throw new Error('首页未提取到任何图书');
  if (!first.updated_at) throw new Error('未找到榜单更新日期，拒绝同步以免翻页时混入不同月份');

  const status = await getJson(`${API_URL}/status?month=${encodeURIComponent(first.chart_month)}`);
  if (status.synced) {
    return { status: 'skipped', chart_month: first.chart_month, message: '该月榜单已同步' };
  }

  const byId = new Map(first.books.map(b => [b.id, b]));
  const maxPages = Math.min(MAX_PAGES, first.max_linked_page);
  let pagesRead = 1;
  for (let page = 2; page <= maxPages; page++) {
    const parsed = await fetchChart(buildPageUrl(page, first.updated_at));
    if (parsed.chart_month !== first.chart_month || parsed.updated_at !== first.updated_at) {
      throw new Error(`第 ${page} 页月份或更新日期与首页不一致`);
    }
    if (parsed.books.length === 0) throw new Error(`第 ${page} 页为空，取消保存`);
    for (const book of parsed.books) {
      if (byId.has(book.id)) throw new Error(`第 ${page} 页出现重复图书：${book.id}`);
      byId.set(book.id, book);
    }
    pagesRead++;
    // 轻量人工触发任务：顺序访问，避免并发请求。
  }

  const books = [...byId.values()].sort((a, b) => a.rank - b.rank);
  const ranks = books.map(b => b.rank);
  if (new Set(ranks).size !== books.length) throw new Error('榜单排名存在重复，取消保存');
  if (books.length < 20) throw new Error(`只解析到 ${books.length} 本，取消保存`);

  return postJson(`${API_URL}/batch`, {
    chart_month: first.chart_month,
    updated_at: first.updated_at,
    source_url: buildPageUrl(1, first.updated_at),
    pages_read: pagesRead,
    books
  });
}

export function initDoubanChart() {
  browser.runtime.onMessage.addListener(message => {
    if (message?.type !== 'douban-chart-sync') return undefined;
    if (running) return Promise.resolve({ status: 'running', message: '同步正在进行' });
    running = true;
    return runChartSync()
      .catch(error => ({ status: 'error', message: String(error?.message || error) }))
      .finally(() => { running = false; });
  });
}
