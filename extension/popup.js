document.getElementById("capture").addEventListener("click", async () => {
  const [tab] = await browser.tabs.query({
    active: true,
    currentWindow: true
  });

  const results = await browser.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => window.getSelection().toString()
  });

  const selectedText = results[0].result;

  console.log(selectedText || "No text selected.");
  alert(selectedText || "No text selected.");
});
