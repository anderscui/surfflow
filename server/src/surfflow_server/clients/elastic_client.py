# coding=utf-8
import hashlib
from pathlib import Path

from elastic_transport import ObjectApiResponse
from toolz import partition_all
from typing import Any

from archaeo.io.docs import LocalFileMetadata
from archaeo.iterable import filter_by_keys

from surfflow_server.config import logger, ES_SERVER, ES_INDEX, ES_MAPPINGS_FILE
from surfflow_server.schemas.files import FileInfo, FileEmbedding

from elasticsearch import Elasticsearch, helpers
from elasticsearch.helpers import BulkIndexError

MAX_OUTLINE_TITLES = 50
MAX_PREVIEW_LEN = 2000
EXPECTED_EMBEDDING_DIM = 4096


def local_file_to_doc(
        file_info: FileInfo,
        metadata: LocalFileMetadata | None = None,
        embedding: FileEmbedding | None = None) -> dict[str, Any]:

    dumped = file_info.model_dump(mode='json')
    converted = filter_by_keys(dumped,
                               keys=('base_dir', 'raw_path', 'name', 'stem', 'extension',
                                     'size', 'creation_time', 'modification_time', 'last_access_time',
                                     'edition', 'year', 'hash', 'tags', 'collection', 'file_type'))

    parent_path = Path(file_info.relative_path).parent
    parent_parts = list(parent_path.parts)
    if parent_parts:
        converted['parent_parts'] = parent_parts
        converted['parent_path'] = str(parent_path)

    if metadata is not None:
        raw_metadata: dict = metadata.metadata or {}
        searchable_metadata = {key: value
                               for key in ("title", "author", "creator", "producer", "artist", "album", "genre")
                               if (value := raw_metadata.get(key))}
        if searchable_metadata:
            converted['metadata'] = searchable_metadata

        page_count = raw_metadata.get('page_count')
        if isinstance(page_count, int) and page_count > 0:
            converted['page_count'] = page_count

        outline = metadata.outline
        if outline:
            outline_titles = [item.title.strip() for item in outline.items if item.title and item.title.strip()]
            if outline_titles:
                converted['outline_titles'] = outline_titles[:MAX_OUTLINE_TITLES]

        preview = (metadata.preview or '').strip()
        if preview:
            converted['preview'] = preview[:MAX_PREVIEW_LEN]

    if embedding is not None:
        actual_dim = len(embedding.embedding)
        if actual_dim != embedding.dimension:
            raise ValueError(f'embedding dim mismatch: emb: {actual_dim}, dim: {embedding.dimension}')
        if actual_dim != EXPECTED_EMBEDDING_DIM:
            raise ValueError(f'embedding dim mismatch: expected dim: {EXPECTED_EMBEDDING_DIM}, actual dim: {actual_dim}')

        converted['embedding'] = embedding.embedding
        converted['embedding_info'] = {
            'dimension': embedding.dimension,
            'provider': embedding.provider,
            'model': embedding.model,
            'text': embedding.text,
        }

    return converted


def convert_local_files(local_files: list, local_metadata: dict, local_embeddings: dict):
    converted = []
    for local_file in local_files[:100000]:
        fi = FileInfo.model_validate(local_file)
        metadata = local_metadata.get(fi.raw_path)
        if metadata is not None:
            metadata = LocalFileMetadata.model_validate(metadata)
        else:
            logger.debug(f'metadata missing: {fi.raw_path}')
        embedding = local_embeddings.get(fi.raw_path)
        if embedding is not None:
            embedding = FileEmbedding.model_validate(embedding)
        converted.append(local_file_to_doc(fi, metadata, embedding))
    return converted


def path_to_document_id(raw_path: str) -> str:
    # return raw_path
    return hashlib.sha256(raw_path.encode("utf-8")).hexdigest()


class ElasticsearchClient:
    def __init__(self, server: str=ES_SERVER):
        self.client = Elasticsearch(hosts=[server])

    def index_exists(self, index) -> bool:
        return self.client.indices.exists(index=index).body

    def create_index(self, index: str, mappings: dict[str, Any]) -> ObjectApiResponse:
        resp = self.client.indices.create(index=index, mappings=mappings)
        logger.debug(f'create es index: {resp}')
        return resp

    def delete_index(self, index: str, timeout='120s') -> ObjectApiResponse:
        resp = self.client.indices.delete(index=index, timeout=timeout)
        logger.debug(f'delete es index: {resp}')
        return resp

    def bulk_index_documents(self, index: str, docs: list, n_bulk=100):
        indexed = 0
        for i, part in enumerate(partition_all(n_bulk, docs)):
            logger.debug(f'indexing partition {i}...')
            try:
                actions = [{'_op_type': 'index',
                            '_index': index,
                            '_id': path_to_document_id(doc['raw_path']),
                            '_source': doc} for doc in part]
                success, _ = helpers.bulk(self.client, index=index, actions=actions)
                indexed += success
            except BulkIndexError as e:
                logger.exception(f'bulk indexing failed: partition: {i}')
                raise
            logger.info(f'partition {i} done, indexed: {indexed}')
        return indexed

    def search_docs(self, index: str,
                    query: str,
                    excludes=None,
                    file_types=None,
                    min_file_size: int | None = None,
                    size=10):

        if excludes is None:
            excludes = ['embedding']

        filters = []
        if file_types is not None:
            filters.append({'terms': {'file_type': file_types}})
        if min_file_size is not None and min_file_size >= 0:
            filters.append({'range': {'size': {"gte": min_file_size}}})

        q = {
            "bool": {
                "must": [
                    {
                        "match": {
                            "stem": {
                                "query": query,
                                "minimum_should_match": "3<90%",
                                "boost": 1
                            }
                        }
                    }
                ]
            }
        }
        if filters:
            q['bool']['filter'] = filters

        return self.client.search(index=index, query=q, source={'excludes': excludes}, size=size)

    # def knn_search_local_docs(self, index: str, target_field: str, query_vector, k=10, num_candidates=100,
    #                excludes=None, file_types=None, min_file_size=100):
    #     if excludes is None:
    #         excludes = ['embedding']
    #
    #     filters = []
    #     if file_types is not None:
    #         filters.append({'terms': {'file_type': file_types}})
    #     if min_file_size is not None and min_file_size >= 0:
    #         filters.append({'range': {'size': {"gte": min_file_size}}})
    #
    #     q = {
    #         'field': target_field,
    #         'query_vector': query_vector,
    #         'k': k,
    #         'num_candidates': num_candidates
    #     }
    #     if filters:
    #         q['filter'] = filters
    #
    #     return self.client.search(index=index, knn=q, source={'excludes': excludes})
    #
    # def response_to_results(self, resp: ObjectApiResponse, min_score=0.0, search_type=None):
    #     result = resp.body
    #     hits = result.get('hits') or {}
    #     # print(hits)
    #     total = hits.get('total') or {}
    #     total = total.get('value') or 0
    #     max_score = hits.get('max_score') or 0
    #
    #     hits = hits.get('hits') or []
    #
    #     converted = []
    #     for hit in hits:
    #         es_id = hit['_id']
    #         score = hit['_score']
    #         source = hit['_source']
    #         # source is a dict
    #         source['id'] = es_id
    #         source['score'] = score
    #         source['relevance'] = round(score / max_score, 2)
    #         source['parent_path'] = str(Path(source['raw_path']).parent)
    #         source['search_type'] = search_type
    #         if score >= min_score:
    #             converted.append(SearchedFileInfo.load_obj(source))
    #     return SearchedFileResult(total=total,
    #                               max_score=max_score,
    #                               num_hits=len(converted),
    #                               hits=converted)
    #
    # def search_local_docs(self, index: str,
    #                       query: str,
    #                       excludes=None,
    #                       file_types=None,
    #                       min_file_size=100,
    #                       size=10,
    #                       min_score=0.0):
    #     resp = self.search_docs(index, query, excludes, file_types, min_file_size, size=size)
    #     return self.response_to_results(resp, min_score, search_type='words')
    #
    # def search_local_docs_by_embedding(self, index: str,
    #                       query_vector,
    #                       excludes=None,
    #                       file_types=None,
    #                       min_file_size=100,
    #                       size=10,
    #                       min_score=0.0):
    #     resp = self.knn_search_local_docs(index, 'embedding', query_vector, k=size,
    #                                       excludes=excludes, file_types=file_types, min_file_size=min_file_size)
    #     return self.response_to_results(resp, min_score, search_type='embedding')


if __name__ == '__main__':
    from archaeo.io.files import json_load
    client = ElasticsearchClient()
    # exists = client.index_exists(ES_INDEX)
    # if exists:
    #     print(f'index {ES_INDEX} is already existing.')
    #     client.delete_index(ES_INDEX)
    #     print(f'index {ES_INDEX} deleted')
    #
    # mappings = json_load(ES_MAPPINGS_FILE)
    # client.create_index(ES_INDEX, mappings)
    #
    # # index docs
    # local_file_records = json_load('~/Downloads/local_files_260713_1.json')
    # local_file_metadata = json_load('~/Downloads/local_metadata_260713_3.json')
    # local_file_embeddings = json_load('~/Downloads/local_embeddings_260714_2.json')
    # print(len(local_file_records), 'records loaded')
    # print(len(local_file_metadata), 'metadata loaded')
    # print(len(local_file_embeddings), 'embeddings loaded')
    #
    # docs = convert_local_files(local_file_records, local_file_metadata, local_file_embeddings)
    # print(f'{len([1 for doc in docs if doc['embedding'] is not None])} files have embeddings.')
    # client.bulk_index_documents(ES_INDEX, docs, n_bulk=1000)
    # print(f'index docs: done')

    # file_types=['link', 'book', 'video']
    print(client.search_docs(ES_INDEX, query='爱情', excludes=['edition', 'year']))

    # searched_files = client.search_local_docs(ES_INDEX, query='小孩 哲学', size=3)
    # print(searched_files.total, searched_files.num_hits)
    # for file_info in searched_files.hits:
    #     print(file_info)
    #     print()
