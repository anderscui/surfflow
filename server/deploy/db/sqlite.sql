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
