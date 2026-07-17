# coding=utf-8
from enum import StrEnum

from pydantic import BaseModel


class FileAction(StrEnum):
    OPEN = 'open'
    REVEAL = 'reveal'
    COPY_PATH = 'copy_path'
    ARCHIVE = 'archive'


class FileActionRequest(BaseModel):
    action: FileAction
    raw_path: str
