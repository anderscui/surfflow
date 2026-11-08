import {hasChineseText} from "./commons/texts.js";
import {logOperation} from "./api.js";
import {getCurrentPageContext} from "./page_context.js";
import {searchDouban} from "./providers/douban.js";
import {searchAmazonBooks} from "./providers/amazon.js";

async function syncHistory() {
  const DEFAULT_START_TIME = new Date("2000-01-01").getTime();
  const MAX_HISTORY_ITEMS = 10_000_000;
  // const MAX_HISTORY_ITEMS = 10;

  const resp = await fetch(
    "http://127.0.0.1:8000/api/v1/firefox/history/last_sync_time"
  );

  if (!resp.ok) {
    throw new Error(`GET last_hist_sync_time error: HTTP ${resp.status}`);
  }

  const data = await resp.json();
  console.log(`sync time: ${data.last_sync_time}`);

  const startTime = data.last_sync_time ?? DEFAULT_START_TIME;
  const endTime = Date.now();
  console.log("startTime:", new Date(startTime));
  console.log("endTime:", new Date(endTime));

  const items = await browser.history.search({
    text: "",
    startTime: startTime,
    endTime: endTime,
    maxResults: MAX_HISTORY_ITEMS,
  });

  console.log(`total history: ${items.length}`);

  const req_sync = {
    start_time: startTime,
    end_time: endTime,
    items: items,
  };

  const resp_sync = await fetch(
    "http://127.0.0.1:8000/api/v1/firefox/history/sync",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(req_sync),
    }
  );

  if (!resp_sync.ok) {
    throw new Error(`POST sync_hist error: HTTP ${resp_sync.status}`);
  }

  await logOperation({
    action: 'sync_history',

    context: {
      startTime,
      endTime,
      itemCount: items.length,
    },
  });

  const data_sync = await resp_sync.json();
  console.log(`Synced ${data_sync.item_count} items.`);
  alert(`Synced ${data_sync.item_count} items.`);


  return data_sync.item_count;
}

document.getElementById("showSelected").addEventListener("click", async () => {
  let context = await getCurrentPageContext();
  let selectedText = context.text || "No text selected.";

  console.log(selectedText);
  alert(selectedText);
});

document.getElementById("showHistory").addEventListener("click", async () => {
  const item_count = await syncHistory();
  console.log(`成功捞取到 ${item_count} 条历史数据。`);
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

let currentResults = [];

function renderMessage(message) {
  document.getElementById("result").innerHTML = `<p>${message}</p>`;
}

function itemTypeLabel(type) {
  const labels = {
    book: "书",
    book_series: "丛书",
    author: "作者",
    movie: "影视",
    celebrity: "影人",
  };
  return labels[type] ?? type ?? "";
}

function renderResults(items) {
  const resultEl = document.getElementById("result");
  currentResults = items;

  if (!items.length) {
    renderMessage("No results found.");
    return;
  }

  resultEl.innerHTML = items.map((item, index) => `
    <div class="result-item" data-index="${index}">
      <div class="result-title-row">
        <div class="result-title-left">
          <span class="type-badge">${itemTypeLabel(item.item_type)}</span>

          <span class="result-title">
            ${item.title || "Untitled"}
          </span>

          ${
            item.labels?.length
              ? `<span class="item-labels">${item.labels.map(label =>
                    `<span class="item-label">[${label}]</span>`
                  ).join("")}</span>`
              : ""
          }
        </div>

        ${
          item.rating
            ? `
              <div class="rating">
                ★ ${item.rating}
                ${
                  item.rating_count
                    ? `<span class="rating-count">(${item.rating_count.toLocaleString()})</span>`
                    : ""
                }
              </div>
            `
            : ""
        }
      </div>

      ${
        item.meta
          ? `<div class="result-desc">${item.meta}</div>`
          : ""
      }

      ${
        item.status
          ? `<div class="result-status">${item.status}</div>`
          : ""
      }
    </div>
  `).join("");

  document.querySelectorAll(".result-item").forEach(el => {
    el.addEventListener("click", () => {
      renderDetail(currentResults[Number(el.dataset.index)]);
    });
  });
}

function renderDetail(item) {
  const resultEl = document.getElementById("result");

  resultEl.innerHTML = `
    <button id="backToList">← Back</button>

    <article>
      <h3>${item.title || "Untitled"}</h3>
      ${item.rating ? `<p><strong>Rating:</strong> ${item.rating}</p>` : ""}
      ${item.meta ? `<p>${item.meta}</p>` : ""}
      ${item.url ? `<p><a href="${item.url}" target="_blank">Open ${item.source} page</a></p>` : ""}
    </article>
  `;

  document.getElementById("backToList").addEventListener("click", () => {
    renderResults(currentResults);
  });
}


async function searchBooks() {
  try {
    renderMessage("Searching book...");

    const context = await getCurrentPageContext();
    const query = context.text;

    if (!query) {
      renderMessage("No text selected.");
      return;
    }

    const items = hasChineseText(query)
      ? await searchDouban(query, "book")
      : await searchAmazonBooks(query);
    console.log(`book items:`);
    for (let item of items) {
      console.log(item);
    }
    renderResults(items);

    await logOperation({
      action: "search_book",

      pageUrl: context.url,
      pageTitle: context.title,

      context: {
        provider: hasChineseText(query)
          ? "douban"
          : "amazon",

        query,

        resultCount: items.length,
      },
    });

  } catch (err) {
    renderMessage(`Failed: ${err.message}`);
  }
}

async function searchMovies() {
  try {
    renderMessage("Searching movie...");

    const context = await getCurrentPageContext();
    const query = context.text;

    if (!query) {
      renderMessage("No text selected.");
      return;
    }

    const items = await searchDouban(query, "movie");
    console.log(`movie items:`);
    for (let item of items) {
      console.log(item);
    }
    renderResults(items);

    await logOperation({
      action: "search_movie",

      pageUrl: context.url,
      pageTitle: context.title,

      context: {
        provider: "douban",
        query,
        resultCount: items.length,
      },
    });

  } catch (err) {
    renderMessage(`Failed: ${err.message}`);
  }
}

document.getElementById("extractBooks").addEventListener("click", extractBooks);

document.getElementById("searchBooks").addEventListener("click", searchBooks);
document.getElementById("searchMovies").addEventListener("click", searchMovies);

// douban book discovery
const button = document.querySelector('#sync-chart');
const status = document.querySelector('#status');

button.addEventListener('click', async () => {
  button.disabled = true;
  status.textContent = '正在读取榜单并同步到本地数据库…';
  try {
    const result = await browser.runtime.sendMessage({ type: 'douban-chart-sync' });
    if (result.status === 'error') throw new Error(result.message);
    if (result.status === 'skipped' || result.status === 'running') {
      status.textContent = `${result.chart_month || ''} ${result.message}`;
    } else {
      status.textContent = `${result.chart_month}：同步完成\n读取 ${result.pages_read} 页，入库 ${result.books_inserted} 本。`;
    }
  } catch (error) {
    status.textContent = `同步失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
});
