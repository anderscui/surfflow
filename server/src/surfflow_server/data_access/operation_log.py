# coding=utf-8
import json
import sqlite3
import time

from surfflow_server.schemas import OperationLogRequest


def insert_operation_log(
    conn: sqlite3.Connection,
    req: OperationLogRequest,
) -> int:
    created_at = int(time.time() * 1000)

    context = (
        json.dumps(req.context, ensure_ascii=False)
        if req.context is not None
        else None
    )

    with conn:
        cur = conn.execute(
            """
            INSERT INTO operation_log
            (
                action,
                page_url,
                page_title,
                context,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                req.action,
                req.page_url,
                req.page_title,
                context,
                created_at,
            ),
        )

    return cur.lastrowid
