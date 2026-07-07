export function waitForTabComplete(tabId) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      browser.tabs.onUpdated.removeListener(listener);
      reject(new Error("Douban search page loading timeout."));
    }, 15000);

    function listener(updatedTabId, changeInfo, tab) {
      if (updatedTabId === tabId && changeInfo.status === "complete") {
        clearTimeout(timeout);
        browser.tabs.onUpdated.removeListener(listener);
        resolve(tab);
      }
    }

    browser.tabs.onUpdated.addListener(listener);
  });
}
