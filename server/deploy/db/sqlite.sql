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

CREATE TABLE IF NOT EXISTS douban_books
(
    id         TEXT PRIMARY KEY,
    url        TEXT NOT NULL,
    title      TEXT NOT NULL,
    authors    TEXT,
    pub_date   TEXT,
    publisher  TEXT,
    list_price TEXT,
    binding    TEXT,
    raw_info   TEXT
);

CREATE TABLE IF NOT EXISTS douban_book_chart_snapshots
(
    chart_month TEXT PRIMARY KEY,
    updated_at  TEXT,
    source_url  TEXT    NOT NULL,
    fetched_at  TEXT    NOT NULL,
    pages_read  INTEGER NOT NULL,
    books_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS douban_book_chart_entries
(
    chart_month     TEXT    NOT NULL,
    book_id         TEXT    NOT NULL,
    rank            INTEGER NOT NULL,
    subcat          TEXT,
    months_on_chart INTEGER,
    rating          REAL,
    rating_count    INTEGER,
    paper_price     REAL,
    paper_url       TEXT,
    ebook_url       TEXT,
    PRIMARY KEY (chart_month, book_id),
    UNIQUE (chart_month, rank),
    FOREIGN KEY (chart_month) REFERENCES douban_book_chart_snapshots (chart_month),
    FOREIGN KEY (book_id) REFERENCES douban_books (id)
);
CREATE INDEX IF NOT EXISTS idx_douban_book_chart_entries_book
    ON douban_book_chart_entries (book_id);

CREATE TABLE IF NOT EXISTS file_tags (
    raw_path TEXT NOT NULL,
    tagger TEXT NOT NULL,
    tags_version TEXT NOT NULL,
    filename TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (raw_path, tagger, tags_version)
);
CREATE INDEX idx_file_tags_tagger_version
ON file_tags(tagger, tags_version);
