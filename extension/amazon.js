function buildAmazonBookSearchUrl(query) {
  return `https://www.amazon.com/s?k=${encodeURIComponent(query)}&i=stripbooks`;
}

function extractAmazonBookSearchResultsFromPage() {
  function clean(text) {
    return (text || "").replace(/\s+/g, " ").trim();
  }

  function parseRating(text) {
    const m = clean(text).match(/([\d.]+)\s+out of 5 stars/);
    return m ? m[1] : "";
  }

  function parseRatingCount(text) {
    const m = clean(text).replace(/,/g, "").match(/(\d+)/);
    return m ? Number(m[1]) : null;
  }

  function normalizeAmazonUrl(href) {
    if (!href) return "";
    return new URL(href, location.origin).href;
  }

  function extractMeta(item) {
    const metaEl = item.querySelector('[data-cy="title-recipe"] .a-row.a-size-base.a-color-secondary');
    return clean(metaEl?.textContent);
  }

  function extractPrice(item) {
    const priceEl = item.querySelector('[data-cy="price-recipe"] .a-price .a-offscreen');
    return clean(priceEl?.textContent);
  }

  const items = Array.from(
    document.querySelectorAll('[data-component-type="s-search-result"]')
  );

  return items
    .slice(0, 5)
    .map((item) => {
      const linkEl =
        item.querySelector('[data-cy="title-recipe"] a[href*="/dp/"]') ||
        item.querySelector('a[href*="/dp/"]');

      const titleEl =
        item.querySelector('[data-cy="title-recipe"] h2 span') ||
        item.querySelector("h2 span") ||
        item.querySelector(".s-image");

      const ratingEl = item.querySelector(".a-icon-alt");

      const ratingCountEl =
        item.querySelector('[aria-label$="ratings"]') ||
        item.querySelector('[href*="#customerReviews"] span');

      return {
        source: "amazon",
        item_type: "book",

        title: clean(titleEl?.textContent || titleEl?.getAttribute("alt")),
        url: normalizeAmazonUrl(linkEl?.getAttribute("href")),

        rating: parseRating(ratingEl?.textContent),

        rating_count: parseRatingCount(
          ratingCountEl?.getAttribute("aria-label") ||
          ratingCountEl?.textContent
        ),

        rating_count_text: clean(
          ratingCountEl?.getAttribute("aria-label") ||
          ratingCountEl?.textContent
        ),

        meta: extractMeta(item),
        price: extractPrice(item),

        status: "",
        labels: [],
      };
    })
    .filter((item) => item.title || item.url);
}

async function searchAmazonBooks(query) {
  let tab = null;
  console.log(`search amazon...`);
  try {
    const searchUrl = buildAmazonBookSearchUrl(query);
    console.log(searchUrl);
    tab = await browser.tabs.create({
      url: searchUrl,
      active: false,
    });

    await waitForTabComplete(tab.id);

    // Amazon 搜索页也可能有延迟渲染，稍等一下。
    await new Promise((resolve) => setTimeout(resolve, 1500));

    console.log(`page loaded, start to extract amazon books...`);
    const injected = await browser.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractAmazonBookSearchResultsFromPage,
    });
    console.log("amazon items:", injected[0]?.result);

    return injected[0]?.result ?? [];
  } finally {
    if (tab?.id) {
      await browser.tabs.remove(tab.id).catch(() => {});
    }
  }
}
