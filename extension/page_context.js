export async function getCurrentPageContext() {
  const [tab] = await browser.tabs.query({
    active: true,
    currentWindow: true,
  });

  if (!tab?.id) {
    throw new Error("No active tab found.");
  }

  const results = await browser.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => window.getSelection().toString(),
  });

  return {
    text: results[0]?.result?.trim() ?? "",
    url: tab.url ?? "",
    title: tab.title ?? "",
  };
}
