# coding=utf-8
from pydantic import BaseModel


class SearchResult(BaseModel):
    source: str
    raw_path: str
    score: float| None = None
    rank: int | None = None
    matched_text: str | None = None
    metadata: dict | None = None
