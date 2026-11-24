# coding=utf-8
import sqlite3

from collections.abc import Iterator, Sequence

from archaeo.schemas.rag.docs import Document, Article, Chunk


def save_rag_document(
    conn: sqlite3.Connection,
    document: Document,
    articles: Sequence[Article],
    chunks: Sequence[Chunk],
) -> None:
    """保存完整文档；相同 ID 的旧数据会被替换。"""
    article_ids = {article.id for article in articles}

    if len(article_ids) != len(articles):
        raise ValueError('Duplicate article IDs')

    if len({chunk.id for chunk in chunks}) != len(chunks):
        raise ValueError('Duplicate chunk IDs')

    for article in articles:
        if article.document_id != document.id:
            raise ValueError(f'Invalid document_id: {article.id}')

    for chunk in chunks:
        if chunk.document_id != document.id:
            raise ValueError(f'Invalid document_id: {chunk.id}')

        if chunk.article_id not in article_ids:
            raise ValueError(f'Unknown article_id: {chunk.article_id}')

    # 调用方负责事务；conn 应启用 PRAGMA foreign_keys=ON
    conn.execute(
        'DELETE FROM rag_documents WHERE id = ?',
        (document.id,),
    )

    conn.execute(
        '''
        INSERT INTO rag_documents (
            id, collection, source_type, published_at, data
        ) VALUES (?, ?, ?, ?, ?)
        ''',
        (
            document.id,
            document.collection,
            document.source_type,
            document.published_at.isoformat()
            if document.published_at else None,
            document.model_dump_json(),
        ),
    )

    conn.executemany(
        '''
        INSERT INTO rag_articles (
            id, document_id, article_order, data
        ) VALUES (?, ?, ?, ?)
        ''',
        (
            (
                article.id,
                article.document_id,
                article.order,
                article.model_dump_json(),
            )
            for article in articles
        ),
    )

    conn.executemany(
        '''
        INSERT INTO rag_chunks (
            id, document_id, article_id, chunk_index, data
        ) VALUES (?, ?, ?, ?, ?)
        ''',
        (
            (
                chunk.id,
                chunk.document_id,
                chunk.article_id,
                chunk.index,
                chunk.model_dump_json(),
            )
            for chunk in chunks
        ),
    )


def get_rag_document(
    conn: sqlite3.Connection,
    document_id: str,
) -> Document | None:
    row = conn.execute(
        'SELECT data FROM rag_documents WHERE id = ?',
        (document_id,),
    ).fetchone()

    return Document.model_validate_json(row[0]) if row else None


def get_rag_articles(
    conn: sqlite3.Connection,
    document_id: str,
) -> list[Article]:
    rows = conn.execute(
        '''
        SELECT data FROM rag_articles
        WHERE document_id = ?
        ORDER BY article_order, id
        ''',
        (document_id,),
    ).fetchall()

    return [Article.model_validate_json(row[0]) for row in rows]


def get_rag_chunks(
    conn: sqlite3.Connection,
    document_id: str,
) -> list[Chunk]:
    rows = conn.execute(
        '''
        SELECT data FROM rag_chunks
        WHERE document_id = ?
        ORDER BY article_id, chunk_index, id
        ''',
        (document_id,),
    ).fetchall()

    return [Chunk.model_validate_json(row[0]) for row in rows]


def iter_rag_chunks(
    conn: sqlite3.Connection,
    batch_size: int = 500,
) -> Iterator[list[Chunk]]:
    """分批读取全部 Chunk，用于 Elasticsearch 和 Embedding。"""
    if batch_size <= 0:
        raise ValueError('batch_size must be positive')

    cursor = conn.execute(
        '''
        SELECT data FROM rag_chunks
        ORDER BY document_id, article_id, chunk_index, id
        '''
    )

    while rows := cursor.fetchmany(batch_size):
        yield [
            Chunk.model_validate_json(row[0])
            for row in rows
        ]


def count_rag_chunks(
    conn: sqlite3.Connection,
    document_id: str | None = None,
) -> int:
    if document_id is None:
        row = conn.execute(
            'SELECT COUNT(*) FROM rag_chunks'
        ).fetchone()
    else:
        row = conn.execute(
            '''
            SELECT COUNT(*) FROM rag_chunks
            WHERE document_id = ?
            ''',
            (document_id,),
        ).fetchone()

    return row[0]


def list_rag_document_ids(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        'SELECT id FROM rag_documents ORDER BY id'
    ).fetchall()

    return [row[0] for row in rows]
