# coding=utf-8
import sqlite3
from datetime import datetime, timezone

from surfflow_server.schemas import ChartBookSyncStatus, ChartBatch

DOUBAN_BOOK_CHART_SYNC_STATUS_SQL = """
    SELECT chart_month, books_count FROM douban_book_chart_snapshots WHERE chart_month = ?
"""

def get_book_chart_sync_status(conn: sqlite3.Connection,
                               month: str):
    row = conn.execute(DOUBAN_BOOK_CHART_SYNC_STATUS_SQL, (month,)).fetchone()
    return ChartBookSyncStatus(chart_month=month,
                               synced=row is not None,
                               books_count=row['books_count'] if row else 0)


def save_chart(conn: sqlite3.Connection,
               batch: ChartBatch):
    now = datetime.now(timezone.utc).isoformat()

    # Lock before checking existence, so two concurrent requests cannot both insert.
    conn.execute('BEGIN IMMEDIATE')
    found = conn.execute(
        'SELECT 1 FROM douban_book_chart_snapshots WHERE chart_month = ?',
        (batch.chart_month,),
    ).fetchone()
    if found:
        return {'status': 'skipped', 'chart_month': batch.chart_month, 'message': '该月榜单已同步'}

    conn.executemany('''
        INSERT INTO douban_books
        (id, url, title, authors, pub_date, publisher, list_price, binding, raw_info)
        VALUES (:id, :url, :title, :authors, :pub_date, :publisher, :list_price, :binding, :raw_info)
        ON CONFLICT(id) DO UPDATE SET
            url=excluded.url, title=excluded.title, authors=excluded.authors,
            pub_date=excluded.pub_date, publisher=excluded.publisher,
            list_price=excluded.list_price, binding=excluded.binding,
            raw_info=excluded.raw_info
    ''', [book.model_dump(include={
        'id', 'url', 'title', 'authors', 'pub_date', 'publisher',
        'list_price', 'binding', 'raw_info'
    }) for book in batch.books])

    conn.execute('''
        INSERT INTO douban_book_chart_snapshots
        (chart_month, updated_at, source_url, fetched_at, pages_read, books_count)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (batch.chart_month, batch.updated_at, batch.source_url, now, batch.pages_read, len(batch.books)))

    conn.executemany('''
        INSERT INTO douban_book_chart_entries
        (chart_month, book_id, rank, subcat, months_on_chart, rating,
         rating_count, paper_price, paper_url, ebook_url)
        VALUES (:chart_month, :book_id, :rank, :subcat, :months_on_chart, :rating,
                :rating_count, :paper_price, :paper_url, :ebook_url)
    ''', [dict(
        chart_month=batch.chart_month, book_id=book.id, rank=book.rank,
        subcat=book.subcat, months_on_chart=book.months_on_chart,
        rating=book.rating, rating_count=book.rating_count,
        paper_price=book.paper_price, paper_url=book.paper_url, ebook_url=book.ebook_url,
    ) for book in batch.books])

    return {
        'status': 'success', 'chart_month': batch.chart_month,
        'pages_read': batch.pages_read, 'books_inserted': len(batch.books)
    }
