// Parse a single Douban /latest page. No DOM access outside this module.
const clean = value => (value ?? '').replace(/\s+/g, ' ').trim();
const absoluteUrl = (href, base) => href ? new URL(href, base).href : null;
const firstNumber = text => {
  const match = clean(text).match(/\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : null;
};

function parsePublicationInfo(text) {
  const raw_info = clean(text);
  const parts = raw_info.split(/\s*\/\s*/).map(clean);
  const dateIndex = parts.findIndex(part => /^(?:19|20)\d{2}(?:[-./年]\d{1,2}){0,2}(?:日)?$/.test(part));
  if (dateIndex === -1) {
    return { authors: null, pub_date: null, publisher: null,
      list_price: null, binding: null, raw_info };
  }

  const afterDate = parts.slice(dateIndex + 1);
  const publisher = afterDate.shift() || null;
  let binding = null;
  if (afterDate.length && /(?:精装|平装|假精装|软精装|简装|盒装|线装|锁线|胶装|hardcover|paperback)/i.test(afterDate.at(-1))) {
    binding = afterDate.pop();
  }
  return {
    authors: parts.slice(0, dateIndex).join(' / ') || null,
    pub_date: parts[dateIndex], publisher,
    list_price: afterDate.join(' / ') || null,
    binding, raw_info,
  };
}

function parseBook(li, pageUrl) {
  const link = li.querySelector('h2 a[href*="/subject/"], a[href*="/subject/"]');
  const url = absoluteUrl(link?.getAttribute('href'), pageUrl);
  const id = url?.match(/\/subject\/(\d+)\/?/)?.[1];
  const title = clean(link?.textContent);
  if (!id || !title) throw new Error(`无法解析图书的 ID 或书名：${clean(li.textContent).slice(0, 80)}`);

  const ratingText = clean(li.querySelector('.subject-rating .font-small')?.textContent);
  const rating = /^\d{1,2}(?:\.\d+)?$/.test(ratingText) ? Number(ratingText) : null;
  const ratingCountText = clean(li.querySelector('.subject-rating')?.textContent);
  const ratingCountMatch = ratingCountText.match(/[（(]\s*([\d,]+)\s*人评价\s*[)）]/);
  const links = [...li.querySelectorAll('a[href]')];
  const paper = links.find(a => /纸质版\s*\d/.test(clean(a.textContent)));
  const ebook = links.find(a => /(?:去看电子版|电子版|阅读电子版)/.test(clean(a.textContent)));

  return {
    id, url, title,
    ...parsePublicationInfo(li.querySelector('.subject-abstract')?.textContent),
    rating: rating !== null && rating <= 10 ? rating : null,
    rating_count: ratingCountMatch ? Number(ratingCountMatch[1].replaceAll(',', '')) : null,
    paper_price: firstNumber(paper?.textContent),
    paper_url: absoluteUrl(paper?.getAttribute('href'), pageUrl),
    ebook_url: absoluteUrl(ebook?.getAttribute('href'), pageUrl),
  };
}

export function parseLatestPage(html, pageUrl) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const list = doc.querySelector('ul.chart-dashed-list');
  if (!list) throw new Error('找不到新书列表 ul.chart-dashed-list（可能触发访问限制或页面已改版）');

  const entries = [...list.querySelectorAll(':scope > li.media, :scope > li')];
  if (!entries.length) throw new Error('新书列表为空，拒绝保存这次同步');
  const books = entries.map(li => parseBook(li, pageUrl));

  const current = new URL(pageUrl);
  const numberedPages = [...doc.querySelectorAll('.paginator a[href]')]
    .map(a => new URL(a.getAttribute('href'), pageUrl))
    .filter(url => url.origin === current.origin && url.pathname === '/latest')
    .map(url => Number(url.searchParams.get('p')))
    .filter(page => Number.isInteger(page) && page > 0);
  const pageNumber = Number(current.searchParams.get('p') || '1');
  const maxLinkedPage = Math.max(pageNumber, ...numberedPages);
  const hasNext = [...doc.querySelectorAll('.paginator .next a[href], .paginator a[href]')]
    .some(a => /后页|下一页|next/i.test(clean(a.textContent)));

  return { books, page_number: pageNumber, max_linked_page: maxLinkedPage, has_next: hasNext };
}
