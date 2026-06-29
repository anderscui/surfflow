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

document.getElementById("extractBooks").addEventListener("click", extractBooks);
