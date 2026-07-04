# coding=utf-8
import time
import sqlite3

from surfflow_server.schemas import FirefoxHistorySyncRequest


def now_ms() -> int:
    return int(time.time() * 1000)


def get_last_history_sync_time(conn: sqlite3.Connection) -> float | None:
    row = conn.execute(
        "SELECT MAX(end_time) AS last_sync_time FROM ff_history_sync"
    ).fetchone()
    return row["last_sync_time"] if row and row["last_sync_time"] is not None else None


def save_sync_op(
    conn: sqlite3.Connection,
    req: FirefoxHistorySyncRequest
) -> int:
    created_at = int(time.time() * 1000)
    items = [item for item in req.items if item.url]

    with conn:
        cur = conn.execute(
            """
            INSERT INTO ff_history_sync
            (start_time, end_time, item_count, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (req.start_time, req.end_time, len(items), created_at),
        )
        sync_id = cur.lastrowid

        conn.executemany(
            """
            INSERT INTO ff_history_item_snapshot
            (sync_id, firefox_id, url, title, last_visit_time, visit_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    sync_id,
                    item.id,
                    item.url,
                    item.title,
                    item.lastVisitTime,
                    item.visitCount,
                )
                for item in items
            ],
        )

        conn.executemany(
            """
            INSERT INTO ff_history_item
            (url, firefox_id, title, last_visit_time, visit_count, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                firefox_id = excluded.firefox_id,
                title = excluded.title,
                last_visit_time = excluded.last_visit_time,
                visit_count = excluded.visit_count,
                updated_at = excluded.updated_at
            """,
            [
                (
                    item.url,
                    item.id,
                    item.title,
                    item.lastVisitTime,
                    item.visitCount,
                    created_at,
                )
                for item in items
            ],
        )

    return sync_id
