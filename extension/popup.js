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

  // const q = encodeURIComponent(selectedText);
  // browser.tabs.create({
  //   url: `http://www.douban.com/search?q=${q}`
  // });
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

function renderResults(items) {
  const resultEl = document.getElementById("result");
  currentResults = items;

  if (!items.length) {
    renderMessage("No results found.");
    return;
  }

  resultEl.innerHTML = items.map((item, index) => `
    <article>
      <h4>${item.title || "Untitled"}</h4>
      ${item.rating ? `<p><strong>Rating:</strong> ${item.rating}</p>` : ""}
      ${item.meta ? `<p>${item.meta}</p>` : ""}
      <button data-index="${index}" class="detail-btn">Details</button>
    </article>
  `).join("");

  document.querySelectorAll(".detail-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const item = currentResults[Number(btn.dataset.index)];
      renderDetail(item);
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
      ${item.url ? `<p><a href="${item.url}" target="_blank">Open Douban</a></p>` : ""}
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

    if (!hasChineseText(query)) {
      renderMessage("English book lookup will use Amazon + Goodreads later.");
      return;
    }

    const items = await searchDouban(query, "book");
    renderResults(items);
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
    renderResults(items);
  } catch (err) {
    renderMessage(`Failed: ${err.message}`);
  }
}

document.getElementById("extractBooks").addEventListener("click", extractBooks);

document.getElementById("searchBooks").addEventListener("click", searchBooks);
document.getElementById("searchMovies").addEventListener("click", searchMovies);
