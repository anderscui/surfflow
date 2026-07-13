# coding=utf-8
from archaeo.llm_providers import BaseLlmProvider


class LlmEmbedder:
    def __init__(self,
                 provider: BaseLlmProvider):
        self.provider = provider

    def embed_text(self, text: str):
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]):
        return self.provider.embed_batch(texts)
