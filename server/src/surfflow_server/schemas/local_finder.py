# coding=utf-8
from pydantic import BaseModel


class RevealFileRequest(BaseModel):
    raw_path: str
