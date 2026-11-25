# coding=utf-8
from pathlib import Path

from archaeo.io.epub_docs import parse_epub_doc
from archaeo.io.files import list_files
from archaeo.rag.chunking import chunk_articles
from elasticsearch import Elasticsearch

from surfflow_server.config import SURFFLOW_DB, ES_SERVER, ES_INDEX_SURFFLOW_DOC
from surfflow_server.data_access.database import connect_db
from surfflow_server.data_access.rag import save_rag_document, count_rag_chunks, list_rag_document_ids, \
    get_rag_document, get_rag_articles, get_rag_chunks
from surfflow_server.rag.embedding import embed_texts
from surfflow_server.rag.indexing.dense import index_chunk_embeddings
from surfflow_server.rag.indexing.es_indexer import parse_magazine_filename, parse_issue_date, index_chunks


def save_magazine_rag_docs(source_dir: str | Path,
                           max_chars: int=3000):
    files = sorted(list_files(source_dir, '*.epub'))

    total_docs = 0
    total_articles = 0
    total_chunks = 0

    parsed = set()
    with connect_db(SURFFLOW_DB) as conn:
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

            save_rag_document(conn, doc, articles, all_chunks)

            total_docs += 1
            total_articles += len(articles)
            total_chunks += len(all_chunks)

    print(f'indexed: {total_docs} docs, {total_articles} articles, {total_chunks} chunks')


def get_rag_chunk_count():
    with connect_db(SURFFLOW_DB) as conn:
        return count_rag_chunks(conn, document_id=None)


def get_all_doc_ids():
    with connect_db(SURFFLOW_DB) as conn:
        return list_rag_document_ids(conn)


def index_magazines_from_db(es, index_name: str):
    total = 0

    with connect_db(SURFFLOW_DB) as conn:
        for document_id in list_rag_document_ids(conn):
            doc = get_rag_document(conn, document_id)
            articles = get_rag_articles(conn, document_id)
            chunks = get_rag_chunks(conn, document_id)

            assert doc is not None

            print(doc.title, len(articles), len(chunks))

            index_chunks(
                es, doc, articles, chunks,
                index_name=index_name,
            )
            total += len(chunks)
            print()

    es.indices.refresh(index=index_name)
    print(f'Indexed {total} chunks')


def index_magazine_embeddings_from_db(es, index_name: str):
    total = 0

    with connect_db(SURFFLOW_DB) as conn:
        for document_id in list_rag_document_ids(conn):
            doc = get_rag_document(conn, document_id)
            articles = get_rag_articles(conn, document_id)
            chunks = get_rag_chunks(conn, document_id)

            assert doc is not None

            print('indexing:', doc.title, len(articles), len(chunks))

            indexed = index_chunk_embeddings(es, chunks, embed_texts, ES_INDEX_SURFFLOW_DOC, batch_size=10, skip_existing=True)
            total += indexed
            print()

    es.indices.refresh(index=index_name)
    print(f'Indexed {total} chunks')


def add_dense_vector_field(
    es: Elasticsearch,
    index_name: str,
    field_name: str = 'embedding_06b',
    dims: int = 1024,
):
    es.indices.put_mapping(
        index=index_name,
        properties={
            field_name: {
                'type': 'dense_vector',
                'dims': dims,
                'index': True,
                'similarity': 'cosine',
            }
        },
    )


def show_embedding_field_count(es: Elasticsearch):
    for field in ['embedding', 'embedding_06b', 'embedding_gamma_740m']:
        count = es.count(
            index=ES_INDEX_SURFFLOW_DOC,
            query={'exists': {'field': field}},
        )['count']

        print(field, count)


def remove_embedding_fields(
    es: Elasticsearch,
    index_name: str,
    fields: list[str] | None = None,
):
    if fields is None:
        fields = ['embedding', 'embedding_gamma_740m']

    response = es.update_by_query(
        index=index_name,
        body={
            'query': {
                'bool': {
                    'should': [
                        {'exists': {'field': field}}
                        for field in fields
                    ],
                    'minimum_should_match': 1,
                },
            },
            'script': {
                'source': '''
                    for (def field : params.fields) {
                        ctx._source.remove(field);
                    }
                ''',
                'lang': 'painless',
                'params': {
                    'fields': fields,
                },
            },
        },
        conflicts='proceed',
        refresh=True,
        wait_for_completion=True,
    )

    return response


if __name__ == '__main__':
    import time

    # start = time.time()
    # source_dir = '~/data/dev/surfflow/magazines/epub'
    # save_magazine_rag_docs(source_dir)
    # print(f'time elapsed: {time.time() - start:.3f}')

    # print(get_rag_chunk_count())
    # all_doc_ids = get_all_doc_ids()
    # print(f'found {len(all_doc_ids)} docs: {all_doc_ids[:2]}')

    es = Elasticsearch(ES_SERVER)
    # index_magazines_from_db(es, index_name=ES_INDEX_SURFFLOW_DOC)
    # index_magazine_embeddings_from_db(es, ES_INDEX_SURFFLOW_DOC)

    # add_dense_vector_field(es, ES_INDEX_SURFFLOW_DOC, field_name='embedding_06b', dims=1024)
    # add_dense_vector_field(es, ES_INDEX_SURFFLOW_DOC, field_name='embedding_gamma_740m', dims=768)
    show_embedding_field_count(es)
    # print(remove_embedding_fields(es, ES_INDEX_SURFFLOW_DOC, fields=['embedding', 'embedding_gamma_740m']))
