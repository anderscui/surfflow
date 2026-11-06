CREATE TABLE IF NOT EXISTS ff_history_sync (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time INTEGER,
    end_time INTEGER NOT NULL,
    item_count INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ff_history_item (
    url TEXT PRIMARY KEY,
    firefox_id TEXT,
    title TEXT,
    last_visit_time INTEGER,
    visit_count INTEGER,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ff_history_item_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_id INTEGER NOT NULL,
    firefox_id TEXT,
    url TEXT NOT NULL,
    title TEXT,
    last_visit_time INTEGER,
    visit_count INTEGER,
    FOREIGN KEY(sync_id) REFERENCES ff_history_sync(id)
);

CREATE INDEX IF NOT EXISTS idx_ff_history_item_last_visit_time
ON ff_history_item(last_visit_time);

CREATE INDEX IF NOT EXISTS idx_ff_history_snapshot_sync_id
ON ff_history_item_snapshot(sync_id);

CREATE TABLE IF NOT EXISTS operation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    action TEXT NOT NULL,

    page_url TEXT,
    page_title TEXT,

    context TEXT,

    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_operation_log_created_at
ON operation_log(created_at);

CREATE INDEX IF NOT EXISTS idx_operation_log_action
ON operation_log(action);

CREATE TABLE IF NOT EXISTS ff_downloads
(
    source_id      TEXT    NOT NULL,
    download_id    INTEGER NOT NULL,
    url            TEXT    NOT NULL,
    final_url      TEXT,
    referrer       TEXT,
    filename       TEXT,
    mime           TEXT,
    start_time     TEXT,
    end_time       TEXT,
    state          TEXT    NOT NULL,
    total_bytes    INTEGER,
    bytes_received INTEGER,
    exists_on_disk INTEGER,
    error          TEXT,
    updated_at     TEXT    NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (source_id, download_id)
);

CREATE INDEX IF NOT EXISTS idx_downloads_start_time ON ff_downloads (start_time);
CREATE INDEX IF NOT EXISTS idx_downloads_filename ON ff_downloads (filename);
