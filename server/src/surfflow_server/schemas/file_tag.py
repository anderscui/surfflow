# coding=utf-8
from pydantic import BaseModel


class FileTagInput(BaseModel):
    raw_path: str
    filename: str


class FileTagRecord(BaseModel):
    raw_path: str
    tagger: str
    tags_version: str
    filename: str
    tags: list[str]
