# coding=utf-8
from elasticsearch import Elasticsearch

from surfflow_server.config import ES_INDEX_SURFFLOW_DOC, ES_DOC_MAPPINGS_FILE, ES_SERVER


def create_chunk_index(es: Elasticsearch, mappings):
    if not es.indices.exists(index=ES_INDEX_SURFFLOW_DOC):
        es.indices.create(
            index=ES_INDEX_SURFFLOW_DOC,
            body=mappings,
        )


if __name__ == '__main__':
    from archaeo.io.files import json_load

    es = Elasticsearch(ES_SERVER)
    mappings = json_load(ES_DOC_MAPPINGS_FILE)
    create_chunk_index(es, mappings)
