# coding=utf-8
from collections.abc import Callable, Sequence
from time import perf_counter

from elasticsearch import Elasticsearch, helpers

from archaeo.schemas.rag.docs import Chunk

# VECTOR_FIELD = 'embedding'
# EMBEDDING_DIMS = 4096
VECTOR_FIELD = 'embedding_06b'
EMBEDDING_DIMS = 1024


def get_embedded_chunk_ids(
    es: Elasticsearch,
    chunk_ids: list[str],
    index_name: str,
) -> set[str]:
    """查询当前批次中已经存在向量的 Chunk ID。"""
    if not chunk_ids:
        return set()

    response = es.search(
        index=index_name,
        size=len(chunk_ids),
        query={
            'bool': {
                'filter': [
                    {'ids': {'values': chunk_ids}},
                    {'exists': {'field': VECTOR_FIELD}},
                ],
            }
        },
        source=False,
    )

    return {
        hit['_id']
        for hit in response['hits']['hits']
    }


def index_chunk_embeddings(
    es: Elasticsearch,
    chunks: Sequence[Chunk],
    embed_fn: Callable[[list[str]], list[list[float]]],
    index_name: str,
    batch_size: int = 8,
    skip_existing: bool = True,
) -> int:
    """向现有 ES Chunk 文档添加 Embedding。"""
    if batch_size <= 0:
        raise ValueError('batch_size must be positive')

    chunk_ids = [chunk.id for chunk in chunks]

    existing = (
        get_embedded_chunk_ids(es, chunk_ids, index_name)
        if skip_existing else set()
    )

    pending = [
        chunk for chunk in chunks
        if chunk.id not in existing
    ]

    indexed = 0

    for start in range(0, len(pending), batch_size):
        batch = pending[start:start + batch_size]

        start = perf_counter()
        vectors = embed_fn([chunk.text for chunk in batch])
        embed_time = perf_counter() - start
        print(f'embed={embed_time:.2f}s')

        if len(vectors) != len(batch):
            raise ValueError('Embedding count mismatch')

        actions = []

        for chunk, vector in zip(batch, vectors):
            if len(vector) != EMBEDDING_DIMS:
                raise ValueError(
                    f'Invalid dimension: {chunk.id}'
                )

            actions.append({
                '_op_type': 'update',
                '_index': index_name,
                '_id': chunk.id,
                'doc': {
                    VECTOR_FIELD: vector,
                },
            })

        for ok, result in helpers.streaming_bulk(
            es,
            actions,
            raise_on_error=True,
            yield_ok=True,
            max_retries=3,
        ):
            if ok:
                indexed += 1

    return indexed
