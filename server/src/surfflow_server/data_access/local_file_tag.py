# coding=utf-8
import json
import sqlite3
from collections.abc import Iterable

from surfflow_server.schemas.file_tag import FileTagRecord


def get_file_tags(
    conn: sqlite3.Connection,
    raw_paths: list[str],
    *,
    tagger: str,
    tags_version: str,
) -> dict[str, FileTagRecord]:
    if not raw_paths:
        return {}
    found = {}
    # SQLite has a limit on the number of bound parameters.
    with conn:
        for start in range(0, len(raw_paths), 500):
            chunk = raw_paths[start:start + 500]
            placeholders = ','.join('?' for _ in chunk)
            rows = conn.execute(
                f'''SELECT raw_path, tagger, tags_version, filename, tags_json
                    FROM file_tags
                    WHERE tagger = ? AND tags_version = ?
                    AND raw_path IN ({placeholders})''',
                [tagger, tags_version, *chunk],
            )
            for row in rows:
                found[row['raw_path']] = FileTagRecord(
                    raw_path=row['raw_path'],
                    tagger=row['tagger'],
                    tags_version=row['tags_version'],
                    filename=row['filename'],
                    tags=json.loads(row['tags_json']),
                )
    return found


def update_file_tags(conn: sqlite3.Connection, records: Iterable[FileTagRecord]) -> None:
    rows = [
        (
            r.raw_path, r.tagger, r.tags_version,
            r.filename, json.dumps(r.tags, ensure_ascii=False),
        )
        for r in records
    ]
    if not rows:
        return
    with conn:
        conn.executemany(
            '''INSERT INTO file_tags
               (raw_path, tagger, tags_version, filename, tags_json)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(raw_path, tagger, tags_version)
               DO UPDATE SET
                   filename = excluded.filename,
                   tags_json = excluded.tags_json,
                   updated_at = CURRENT_TIMESTAMP''',
            rows,
        )
