# coding=utf-8
import sqlite3

from surfflow_server.schemas import FirefoxDownload, FirefoxDownloadBatch, FirefoxDownloadSyncResult


UPSERT_SQL = '''
    INSERT INTO ff_downloads (
        source_id, download_id, url, final_url, referrer,
        filename, mime, start_time, end_time, state,
        total_bytes, bytes_received, exists_on_disk, error
    )
    VALUES (
        :source_id, :download_id, :url, :final_url, :referrer,
        :filename, :mime, :start_time, :end_time, :state,
        :total_bytes, :bytes_received, :exists_on_disk, :error
    )
    ON CONFLICT(source_id, download_id) DO UPDATE SET
        url = excluded.url,
        final_url = excluded.final_url,
        referrer = excluded.referrer,
        filename = excluded.filename,
        mime = excluded.mime,
        start_time = excluded.start_time,
        end_time = excluded.end_time,
        state = excluded.state,
        total_bytes = excluded.total_bytes,
        bytes_received = excluded.bytes_received,
        exists_on_disk = excluded.exists_on_disk,
        error = excluded.error,
        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
'''


def record_to_params(record: FirefoxDownload) -> dict:
    data = record.model_dump()
    value = data['exists_on_disk']

    if value is not None:
        data['exists_on_disk'] = int(value)

    return data


def upsert_downloads(conn: sqlite3.Connection,
                     records: list[FirefoxDownload]) -> int:
    if not records:
        return 0

    params = [record_to_params(item) for item in records]
    conn.executemany(UPSERT_SQL, params)
    return len(records)


def list_downloads(
    conn: sqlite3.Connection,
    source_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    sql = 'SELECT * FROM ff_downloads WHERE 1 = 1'
    params = []

    if source_id is not None:
        sql += ' AND source_id = ?'
        params.append(source_id)

    sql += '''
        ORDER BY start_time DESC, download_id DESC
        LIMIT ? OFFSET ?
    '''
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]
