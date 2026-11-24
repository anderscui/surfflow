# coding=utf-8
from dataclasses import dataclass

from elasticsearch import Elasticsearch

from surfflow_server.config import ES_INDEX_SURFFLOW_DOC, ES_SERVER


@dataclass
class SearchHit:
    chunk_id: str
    article_id: str
    document_id: str
    article_title: str
    text: str
    score: float
    collection: str | None = None
    published_at: str | None = None


def search_bm25(
    es: Elasticsearch,
    query: str,
    top_k: int = 10,
    collection: str | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    index_name: str = ES_INDEX_SURFFLOW_DOC,
) -> list[SearchHit]:
    if not query.strip() or top_k <= 0:
        return []

    filters = []

    if collection is not None:
        filters.append({'term': {'collection': collection}})

    if year_start is not None or year_end is not None:
        year_range = {}
        if year_start is not None:
            year_range['gte'] = year_start
        if year_end is not None:
            year_range['lte'] = year_end

        filters.append({'range': {'published_year': year_range}})

    body = {
        'size': top_k,
        'query': {
            'bool': {
                'must': [{
                    'multi_match': {
                        'query': query,
                        'fields': ['title^3', 'text'],
                        'type': 'best_fields',
                    }
                }],
                'filter': filters,
            }
        },
    }

    response = es.search(index=index_name, body=body)

    results = []

    for hit in response['hits']['hits']:
        source = hit['_source']

        results.append(
            SearchHit(
                chunk_id=source['chunk_id'],
                article_id=source['article_id'],
                document_id=source['document_id'],
                article_title=source['title'],
                text=source['text'],
                score=hit['_score'],
                collection=source.get('collection'),
                published_at=source.get('published_at'),
            )
        )

    return results


if __name__ == '__main__':
    es = Elasticsearch(ES_SERVER)
    # query = 'artificial intelligence'
    # query = 'Communist Party'
    # query = 'James Bond'
    # query = 'Era of games'
    query = 'Ukraine Russia'
    # query = 'OpenAI Anthropic Google'
    # query = 'China Japan Korea'
    # query = 'New York socialist mayor'
    # query = 'Wikipedia internet'
    hits = search_bm25(
        es,
        query=query,
        top_k=20,
    )

    found_docs = set()
    for rank, hit in enumerate(hits, 1):
        if hit.document_id in found_docs:
            continue
        found_docs.add(hit.document_id)

        print(f'{rank}. {hit.article_title}')
        print(f'   Score: {hit.score:.3f}')
        print(f'   Collection: {hit.collection}, {hit.published_at}')
        print(f'   {hit.text[:100]}')
        print('-' * 60)
