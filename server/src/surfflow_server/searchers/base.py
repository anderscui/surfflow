# coding=utf-8
from abc import ABC, abstractmethod

from archaeo.io.files import is_relative_to_any
from archaeo.searchers.filesystem.mdfinder import search_files
from surfflow_server.config import SOURCE_DIRS
from surfflow_server.schemas.searchers import SearchResult


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


if __name__ == '__main__':
    searcher = MdfindSearcher()
    for p in searcher.search('归宿 安妮', limit=5):
        print(p.raw_path)
