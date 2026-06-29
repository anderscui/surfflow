# coding=utf-8
from pydantic import BaseModel


class ExtractBookRequest(BaseModel):
    text: str

