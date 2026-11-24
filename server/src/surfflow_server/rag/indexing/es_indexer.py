# coding=utf-8
import re
from datetime import date, datetime
from collections.abc import Iterator
from pathlib import Path

import dateparser
from elasticsearch import Elasticsearch, helpers

from archaeo.schemas.rag.docs import Document, Article, Chunk
from surfflow_server.config import ES_INDEX_SURFFLOW_DOC, ES_SERVER

MAGAZINE_NAMES = {
    'ny': 'the_new_yorker',
    'new_yorker': 'the_new_yorker',

    'tm': 'time',
    'time': 'time',
    'time_magazine': 'time',

    'sa': 'scientific_american',
    'scientific_american': 'scientific_american',

    'te': 'the_economist',
    'economist': 'the_economist',
    'theeconomist': 'the_economist',
    'the_economist': 'the_economist',

    'atlantic': 'the_atlantic',
    'the_atlantic': 'the_atlantic',

    'nb': 'nyrb',  # The New York Review of Books

    'wired': 'wired',
}

DATE_PATTERN = re.compile(
    r'(?<!\d)(20\d{2})[._-]?(\d{2})(?:[._-]?(\d{2}))?(?!\d)'
)


def parse_magazine_filename(path: str | Path) -> tuple[str, str]:
    stem = Path(path).stem

    match = DATE_PATTERN.search(stem)
    if not match:
        raise ValueError(f'Date not found: {stem}')

    year, month, day = match.groups()

    if day:
        issue_date = datetime.strptime(
            f'{year}-{month}-{day}', '%Y-%m-%d'
        ).strftime('%Y-%m-%d')
    else:
        issue_date = datetime.strptime(
            f'{year}-{month}', '%Y-%m'
        ).strftime('%Y-%m')

    name = stem[:match.start()] + stem[match.end():]
    # print(name)
    name = re.sub(r'[\s.\-]+', '_', name).strip('_').lower()

    magazine = MAGAZINE_NAMES.get(name)
    if magazine is None:
        print(issue_date, name, path)
        raise ValueError(f'Unknown magazine: {name}')

    return magazine, issue_date


def make_chunk_actions(
    document: Document,
    articles: list[Article],
    chunks: list[Chunk],
    index_name: str = ES_INDEX_SURFFLOW_DOC,
) -> Iterator[dict]:
    article_map = {article.id: article for article in articles}

    for chunk in chunks:
        article = article_map[chunk.article_id]

        if chunk.document_id != document.id:
            raise ValueError(f'Document mismatch: {chunk.id}')

        published_at = article.published_at or document.published_at

        yield {
            '_op_type': 'index',
            '_index': index_name,
            '_id': chunk.id,
            '_source': {
                'chunk_id': chunk.id,
                'document_id': document.id,
                'article_id': article.id,
                'chunk_index': chunk.index,
                'title': article.title,
                'breadcrumbs': article.breadcrumbs,
                'collection': document.collection,
                'source_type': document.source_type,
                'published_at': (
                    published_at.isoformat() if published_at else None
                ),
                'published_year': (
                    published_at.year if published_at
                    else article.published_year or document.published_year
                ),
                'text': chunk.text,
            },
        }


def index_chunks(
    es: Elasticsearch,
    document: Document,
    articles: list[Article],
    chunks: list[Chunk],
    index_name: str = ES_INDEX_SURFFLOW_DOC,
    batch_size: int = 500,
) -> int:
    actions = make_chunk_actions(
        document, articles, chunks, index_name
    )

    indexed = 0

    for ok, result in helpers.streaming_bulk(
        es,
        actions,
        chunk_size=batch_size,
        raise_on_error=True,
        max_retries=3,
        yield_ok=True,
    ):
        if ok:
            indexed += 1
        else:
            raise RuntimeError(f'Indexing failed: {result}')

    return indexed


def parse_issue_date(issue_date: str):
    dp_settings = {"PREFER_DAY_OF_MONTH": "first"}
    return dateparser.parse(issue_date, settings=dp_settings)


def index_files(source_dir: str | Path, es: Elasticsearch, es_index: str, max_chars: int=3000):
    files = sorted(list_files(source_dir, '*.epub'))

    total_docs = 0
    total_articles = 0
    total_chunks = 0

    parsed = set()
    for file in files:
        mag, issue_date = parse_magazine_filename(file)
        doc_key = f'{mag}-{issue_date}' if issue_date else f'{mag}'
        if doc_key in parsed:
            continue

        parsed.add(doc_key)
        published_at = parse_issue_date(issue_date) if issue_date else None
        if published_at:
            published_at = published_at.date()
        print(doc_key, published_at)
        doc, articles = parse_epub_doc(file, doc_key,
                                       doc_collection=mag,
                                       published_at=published_at)
        all_chunks = chunk_articles(articles, max_chars=max_chars)
        print(doc.title, len(articles), len(all_chunks))
        indexed = index_chunks(es, doc, articles, all_chunks, index_name=es_index)
        es.indices.refresh(index=es_index)

        total_docs += 1
        total_articles += len(articles)
        total_chunks += indexed
        print(f'indexed: {total_docs} docs, {total_articles} articles, {total_chunks} chunks')
    print(f'parsed {len(parsed)} files')


if __name__ == '__main__':
    dt1 = parse_issue_date("2026-09-11")
    dt2 = parse_issue_date("2026-09")
    print(dt1.date(), dt2.date())

    import time
    from archaeo.io.epub_docs import parse_epub_doc
    from archaeo.io.files import get_absolute_path, list_files
    from archaeo.rag.chunking import chunk_articles

    # file = '~/data/dev/surfflow/magazines/epub/TheEconomist.2026.11.21.epub'
    # # file = '~/data/dev/surfflow/magazines/epub/SA_2026-12.epub'
    # file = get_absolute_path(file)
    # print(parse_magazine_filename(file))

    start = time.time()
    source_dir = '~/data/dev/surfflow/magazines/epub'
    es = Elasticsearch(ES_SERVER)
    # max_chars=2000: indexed: 105 docs, 6711 articles, 26150 chunks;44.5mb;13.9s;
    # max_chars=3000: indexed: 105 docs, 6711 articles, 18015 chunks;42.9mb;13.8s;
    # max_chars=4000: indexed: 105 docs, 6711 articles, 14181 chunks;42.1mb;13.6s;
    # max_chars=5000: indexed: 105 docs, 6711 articles, 11931 chunks;41.9mb;12.9s;
    index_files(source_dir, es, es_index=ES_INDEX_SURFFLOW_DOC, max_chars=5000)
    print(f'time elapsed: {time.time() - start:.3f}')

    # doc_key = 'te-2026.11.21'
    # doc, articles = parse_epub_doc(file, doc_key, 'the_economist',
    #                                published_at=date(2026, 11, 21))
    # all_chunks = chunk_articles(articles, max_chars=2000)
    # print('document:', doc.title, doc.id, doc.published_at)
    # print('articles:', len(articles))
    # print(f'chunks: {len(all_chunks)}')
    #
    # es = Elasticsearch(ES_SERVER)
    # count = index_chunks(es,
    #                      document=doc,
    #                      articles=articles,
    #                      chunks=all_chunks)
    # es.indices.refresh(index=ES_INDEX_SURFFLOW_DOC)
    # print(f'indexed {count} chunks')
    # print(es.count(index=ES_INDEX_SURFFLOW_DOC))
