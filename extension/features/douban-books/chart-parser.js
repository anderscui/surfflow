const CATEGORIES = [
  '文学', '小说', '历史文化', '社会纪实', '科学新知',
  '艺术设计', '商业经管', '绘本漫画'
];

const normalize = value => (value || '').replace(/\s+/g, ' ').trim();
const firstNumber = text => {
  const match = normalize(text).match(/\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : null;
};
const absoluteUrl = (href, base) => href ? new URL(href, base).href : null;

function parsePublicationInfo(text) {
  const parts = normalize(text).split(/\s*\/\s*/).map(normalize);
  const dateIndex = parts.findIndex(part => /^(?:19|20)\d{2}(?:[-./]\d{1,2}){0,2}$/.test(part));
  if (dateIndex < 0) {
    return { authors: null, pub_date: null, publisher: null, list_price: null, binding: null, raw_info: normalize(text) };
  }
  const rest = parts.slice(dateIndex + 1);
  const publisher = rest.shift() || null;
  let binding = null;
  if (rest.length && /(?:精装|平装|软精装|简装|盒装|线装|锁线|活腔|胶装|裸脊|函套)/.test(rest.at(-1))) {
    binding = rest.pop();
  }
  const list_price = rest.length ? rest.join(' / ') : null;
  return {
    authors: parts.slice(0, dateIndex).join(' / ') || null,
    pub_date: parts[dateIndex], publisher, list_price, binding,
    raw_info: normalize(text)
  };
}

function findRank(li) {
  const strong = li.querySelector('strong.green-num-box, .green-num-box, strong.fleft');
  const n = firstNumber(strong?.textContent);
  if (n !== null && Number.isInteger(n) && n >= 1 && n <= 1000) return n;
  // 避免把排名浮动数字当成实际名次；此处失败应让整次同步报错。
  return null;
}

function parseBook(li, baseUrl) {
  const link = li.querySelector('h2 a[href*="/subject/"], a.fleft[href*="/subject/"]');
  if (!link) return null;
  const match = link.href.match(/\/subject\/(\d+)/);
  if (!match) return null;

  const infoNode = li.querySelector('p.subject-abstract, .subject-abstract');
  const info = parsePublicationInfo(infoNode?.textContent || '');
  const rank = findRank(li);
  const ratingText = li.querySelector('.subject-rating .font-small')?.textContent.trim();
  const rating = ratingText ? Number(ratingText) : null;
  const text = normalize(li.textContent);
  const ratingCount = text.match(/\(\s*([\d,]+)\s*人评价\s*\)/);
  const months = text.match(/连续上榜\s*(\d+)\s*个月/);
  const paper = [...li.querySelectorAll('a')].find(a => /纸质版\s*\d/.test(a.textContent));
  const ebook = [...li.querySelectorAll('a')].find(a => /去看电子版/.test(a.textContent));
  const category = CATEGORIES.find(c => new RegExp(`(?:^|\\s)${c}(?:\\s|$)`).test(text)) || null;

  if (rank === null) throw new Error(`无法解析排名：${normalize(link.textContent)}`);

  return {
    id: match[1], url: absoluteUrl(link.getAttribute('href'), baseUrl),
    title: normalize(link.textContent), ...info, rank,
    rating: rating !== null && rating <= 10 ? rating : null,
    rating_count: ratingCount ? Number(ratingCount[1].replaceAll(',', '')) : null,
    subcat: category, months_on_chart: months ? Number(months[1]) : 1,
    paper_price: firstNumber(paper?.textContent),
    paper_url: absoluteUrl(paper?.getAttribute('href'), baseUrl),
    ebook_url: absoluteUrl(ebook?.getAttribute('href'), baseUrl)
  };
}

function chartMonth(doc, updatedAt) {
  const title = normalize(doc.querySelector('h1')?.textContent || doc.title);
  const monthMatch = title.match(/(1[0-2]|[1-9])月热门图书榜/);
  if (!monthMatch) throw new Error(`无法识别榜单月份：${title}`);
  const month = Number(monthMatch[1]);
  const ref = updatedAt ? new Date(`${updatedAt}T00:00:00`) : new Date();
  if (Number.isNaN(ref.valueOf())) throw new Error('无效 updated_at');
  const year = ref.getFullYear() - (month > ref.getMonth() + 1 ? 1 : 0);
  return `${year}-${String(month).padStart(2, '0')}`;
}

export function parseChartPage(html, pageUrl) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const list = doc.querySelector('ul.chart-dashed-list');
  if (!list) throw new Error('找不到 ul.chart-dashed-list：可能是反爬页面或网站结构已变化');

  // 最新榜单 URL 没有 updated_at，但分页 URL 通常包含它。
  const original = new URL(pageUrl);
  let updatedAt = original.searchParams.get('updated_at');
  if (!updatedAt) {
    for (const a of doc.querySelectorAll('a[href*="p="][href*="updated_at="]')) {
      const u = new URL(a.getAttribute('href'), pageUrl);
      if (u.pathname === '/chart' && u.searchParams.get('subcat') === 'all') {
        updatedAt = u.searchParams.get('updated_at');
        break;
      }
    }
  }

  const entries = [...list.querySelectorAll(':scope > li')];
  const books = entries.map(li => parseBook(li, pageUrl)).filter(Boolean);
  if (entries.length && books.length !== entries.length) {
    throw new Error(`图书解析不完整：列表 ${entries.length} 条，解析 ${books.length} 条`);
  }
  const pagination = [...doc.querySelectorAll('.paginator a[href]')]
    .map(a => new URL(a.getAttribute('href'), pageUrl))
    .map(a => Number(new URL(a.href).searchParams.get('p')))
    .filter(n => Number.isInteger(n) && n > 0);

  return {
    chart_month: chartMonth(doc, updatedAt),
    updated_at: updatedAt,
    books,
    max_linked_page: pagination.length ? Math.max(...pagination) : 1,
  };
}
