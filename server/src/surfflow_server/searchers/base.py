# coding=utf-8
from abc import ABC, abstractmethod
from collections import defaultdict

from archaeo.io.files import is_relative_to_any
from archaeo.llm_providers import OllamaProvider
from archaeo.searchers.filesystem.mdfinder import search_files

from surfflow_server.clients.elastic_client import ElasticsearchClient
from surfflow_server.config import SOURCE_DIRS, SURFFLOW_EMB_DB, ES_INDEX_LOCAL_FILE
from surfflow_server.embedders.embedding_caches import SqliteEmbeddingCache
from surfflow_server.embedders.text_embedders import LlmEmbedder
from surfflow_server.schemas.searchers import SearchResult, SearchedFileResult

es_client = ElasticsearchClient()


def es_results_to_search_results(source, query, es_result: SearchedFileResult):
    results = []
    for i, hit in enumerate(es_result.hits):
        results.append(SearchResult(
            source=source,
            raw_path=hit.raw_path,
            score=hit.score,
            rank=i + 1,
            matched_text=query
        ))
    return results


class BaseSearcher(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[SearchResult]:
        raise NotImplementedError


class MdfindSearcher(BaseSearcher):
    def __init__(self):
        super().__init__('mdfind')

    def search(self, query: str, limit: int = 20) -> list[SearchResult]:
        paths = search_files(query)
        paths = [p for p in paths if is_relative_to_any(p, SOURCE_DIRS)]
        paths = paths[:limit]
        results = []
        for i, p in enumerate(paths):
            results.append(SearchResult(
                source=self.name,
                raw_path=str(p),
                score=1.0,
                rank=i+1,
                matched_text=query
            ))
        return results


class ElasticKeywordSearcher(BaseSearcher):
    def __init__(self):
        super().__init__('elastic_keyword')

    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[SearchResult]:
        query = query.strip() if query else ''
        if not query:
            return []

        search_result = es_client.search_local_docs(ES_INDEX_LOCAL_FILE, query, size=limit)
        return es_results_to_search_results(self.name, query, search_result)


class ElasticEmbeddingSearcher(BaseSearcher):
    def __init__(self, embedder: LlmEmbedder):
        super().__init__('elastic_embedding')

        self.embedder = embedder

    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[SearchResult]:
        query = query.strip() if query else ''
        if not query:
            return []
        query_embedding = self.embedder.embed_text(query)
        search_result = es_client.search_local_docs_by_embedding(ES_INDEX_LOCAL_FILE, query_embedding, size=limit)
        return es_results_to_search_results(self.name, query, search_result)


class HybridSearcher(BaseSearcher):
    def __init__(
        self,
        searchers: list[BaseSearcher],
        weights: dict[str, float] | None = None,
        rrf_k: int = 60,
    ):
        super().__init__("hybrid")

        self.searchers = searchers
        self.weights = weights or {}
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[SearchResult]:

        candidates: dict[str, SearchResult] = {}
        fused_scores: dict[str, float] = defaultdict(float)
        matched_sources: dict[str, list[str]] = defaultdict(list)

        recall_limit = max(limit * 3, 50)

        for searcher in self.searchers:
            results = searcher.search(query, limit=recall_limit)
            weight = self.weights.get(searcher.name, 1.0)

            for rank, result in enumerate(results, start=1):
                raw_path = result.raw_path

                fused_scores[raw_path] += (
                    weight / (self.rrf_k + rank)
                )

                matched_sources[raw_path].append(searcher.name)

                if raw_path not in candidates:
                    candidates[raw_path] = result

        ranked_paths = sorted(
            fused_scores,
            key=fused_scores.get,
            reverse=True,
        )[:limit]

        final_results: list[SearchResult] = []

        for rank, raw_path in enumerate(ranked_paths, start=1):
            result = candidates[raw_path].model_copy(deep=True)
            result.rank = rank
            result.score = fused_scores[raw_path]
            result.source = ",".join(matched_sources[raw_path])
            final_results.append(result)

        if final_results:
            max_score = final_results[0].score
            if max_score is not None and max_score > 0:
                for result in final_results:
                    result.score /= max_score

        return final_results


def get_default_local_file_searcher():
    mdfind_searcher = MdfindSearcher()
    # for p in mdfind_searcher.search('归宿 安妮', limit=5):
    #     print(p.raw_path)

    cache = SqliteEmbeddingCache(SURFFLOW_EMB_DB)
    embedder = LlmEmbedder(OllamaProvider('qwen3-embedding:8b'), cache)
    es_emb_searcher = ElasticEmbeddingSearcher(embedder)
    # for p in es_emb_searcher.search('叶嘉莹 唐诗宋词', limit=5):
    #     print(p.raw_path)

    print()
    es_kw_searcher = ElasticKeywordSearcher()
    # for p in es_kw_searcher.search('叶嘉莹 唐诗宋词', limit=5):
    #     print(p.raw_path)

    searchers = [
        mdfind_searcher,
        es_kw_searcher,
        es_emb_searcher,
    ]
    weights = {
        mdfind_searcher.name: 1.0,
        es_kw_searcher.name: 1.0,
        es_emb_searcher.name: 1.0,
    }
    file_searcher = HybridSearcher(searchers, weights)
    return file_searcher


if __name__ == '__main__':
    hybrid_searcher = get_default_local_file_searcher()
    for p in hybrid_searcher.search('叶嘉莹 唐诗宋词', limit=10):
        print(p.raw_path)

    print()
    for p in hybrid_searcher.search('AI Agents', limit=10):
        print(p.raw_path)

    print()
    for p in hybrid_searcher.search('中国古典文学', limit=10):
        print(p.raw_path)

    print()
    for p in hybrid_searcher.search('深度学习', limit=10):
        print(p.raw_path)

    print()
    for p in hybrid_searcher.search('大语言模型', limit=10):
        print(p.raw_path)

    print()
    for p in hybrid_searcher.search('初等数学', limit=10):
        print(p.raw_path)

    print()
    for p in hybrid_searcher.search('RAG for Production', limit=10):
        print(p.raw_path)

    print()
    for p in hybrid_searcher.search('金瓶梅', limit=10):
        print(p.raw_path)

    # 数学：它的内容、方法和意义
    print()
    for p in hybrid_searcher.search('文学是什么', limit=10):
        print(p.raw_path)
