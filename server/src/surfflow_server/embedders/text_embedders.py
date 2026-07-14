# coding=utf-8
from archaeo.llm_providers import BaseLlmProvider
from surfflow_server.embedders.embedding_caches import EmbeddingCache, SqliteEmbeddingCache, build_embedding_cache_key


class LlmEmbedder:
    def __init__(self,
                 provider: BaseLlmProvider,
                 cache: EmbeddingCache | None = None):
        self.provider = provider
        self.cache = cache

    def _build_cache_key(self, text: str, **kwargs) -> str:
        return build_embedding_cache_key(
            self.provider.name,
            self.provider.model,
            text,
            **kwargs
        )

    def embed_text(self, text: str, **kwargs) -> list[float]:
        embeddings = self.embed_texts([text], **kwargs)
        if len(embeddings) != 1:
            raise ValueError(
                "embedding count mismatch: "
                f"expected=1, actual={len(embeddings)}"
            )
        return embeddings[0]

    def embed_texts(self, texts: list[str], **kwargs) -> list[list[float]]:
        if not texts:
            return []

        results: list[list[float] | None] = [None] * len(texts)

        missing_texts: list[str] = []
        missing_indices: list[int] = []
        missing_keys: list[str] = []

        for index, text in enumerate(texts):
            cache_key = self._build_cache_key(text, **kwargs)
            cached = self.cache.get(cache_key) if self.cache is not None else None
            if cached is not None:
                results[index] = cached
            else:
                missing_texts.append(text)
                missing_indices.append(index)
                missing_keys.append(cache_key)

        if missing_texts:
            missing_embeddings = self.provider.embed_batch(missing_texts, **kwargs)
            for index, key, embedding in zip(missing_indices, missing_keys, missing_embeddings):
                results[index] = embedding
                if self.cache is not None:
                    self.cache.set(key, embedding)

        if any(embedding is None for embedding in results):
            raise RuntimeError("failed to resolve all embeddings")

        return [embedding for embedding in results if embedding is not None]


if __name__ == '__main__':
    from surfflow_server.config import SURFFLOW_EMB_DB
    cache = SqliteEmbeddingCache(SURFFLOW_EMB_DB)
    embedding = cache.get('key1')
    print(embedding is None, embedding)
    for i in range(10):
        cache.set(f'key{i}', [1, 2, 3])
