async function logOperation({
  action,
  pageUrl,
  pageTitle,
  context,
}) {
  const resp = await fetch(
    "http://127.0.0.1:8000/api/v1/operations/log",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        action,
        page_url: pageUrl,
        page_title: pageTitle,
        context,
      }),
    }
  );

  if (!resp.ok) {
    throw new Error(`logOperation failed: HTTP ${resp.status}`);
  }

  return await resp.json();
}
