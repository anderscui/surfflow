# coding=utf-8
from abc import ABC, abstractmethod


class BaseFileTagger(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier for the classifier configuration (cache key)."""
        ...

    @abstractmethod
    def tag(self, filename: str) -> list[str]:
        """Classify a single filename, returning zero to five tags."""
        ...

    def tag_batch(self, filenames: list[str]) -> list[list[str]]:
        """Return tags in exactly the same order as filenames."""
        return [self.tag(filename) for filename in filenames]
