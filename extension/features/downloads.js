const API_BASE = 'http://127.0.0.1:8000/api/v1/firefox/downloads';
const API_KEY = 'a-random-secret';

const SYNC_DAYS = 30;
const BATCH_SIZE = 200;

let sourceId = null;
let taskQueue = Promise.resolve();


// Serializes sync and incremental updates.
function enqueue(task) {
  taskQueue = taskQueue
    .catch(error => {
      console.error('Previous task failed:', error);
    })
    .then(task);

  return taskQueue;
}


async function getSourceId() {
  const data = await browser.storage.local.get('sourceId');

  if (data.sourceId) {
    return data.sourceId;
  }

  const id = crypto.randomUUID();
  await browser.storage.local.set({ sourceId: id });

  return id;
}


function serializeDownload(item) {
  return {
    source_id: sourceId,
    id: item.id,
    url: item.url,
    finalUrl: item.finalUrl ?? null,
    referrer: item.referrer ?? null,
    filename: item.filename ?? null,
    mime: item.mime ?? null,
    startTime: item.startTime ?? null,
    endTime: item.endTime ?? null,
    state: item.state,
    totalBytes: item.totalBytes ?? null,
    bytesReceived: item.bytesReceived ?? null,
    exists: item.exists ?? null,
    error: item.error ?? null
  };
}


async function postJson(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`HTTP ${response.status}: ${detail}`);
  }

  return response.json();
}


async function saveDownload(item) {
  return postJson('', serializeDownload(item));
}


async function saveBatch(items) {
  const records = items.map(serializeDownload);

  return postJson('/batch', {
    items: records
  });
}


export async function syncDownloads(days = SYNC_DAYS) {
  const query = {
    orderBy: ['-startTime']
  };

  if (days !== null) {
    const since = new Date();
    since.setDate(since.getDate() - days);
    query.startedAfter = since.toISOString();
  }

  const items = await browser.downloads.search(query);

  console.log(`Syncing ${items.length} downloads`);
  console.log(JSON.stringify(items.slice(0, 1), null, 2));

  for (let i = 0; i < items.length; i += BATCH_SIZE) {
    const batch = items.slice(i, i + BATCH_SIZE);
    await saveBatch(batch);
  }

  console.log('Download sync completed');
}


async function refreshDownload(id) {
  const items = await browser.downloads.search({ id });

  if (items.length > 0) {
    await saveDownload(items[0]);
  }
}

function handleDownloadCreated(item) {
  console.log(`A download item created: ${JSON.stringify(item, null, 2)}`);
  enqueue(() => saveDownload(item)).catch(console.error);
}

function handleDownloadChanged(delta) {
  const state = delta.state?.current;

  if (
    state !== "complete" &&
    state !== "interrupted" &&
    delta.filename === undefined
  ) {
    return;
  }

  enqueue(() => refreshDownload(delta.id)).catch(console.error);
}

export function initDownloads() {
  browser.downloads.onCreated.addListener(handleDownloadCreated);
  browser.downloads.onChanged.addListener(handleDownloadChanged);

  enqueue(async () => {
    sourceId = await getSourceId();
    await syncDownloads();
  }).catch(console.error);

  // Optional manual full sync through extension console:
  // enqueue(() => syncDownloads(null));
}
