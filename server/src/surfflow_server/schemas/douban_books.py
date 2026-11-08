# coding=utf-8
import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ChartBookSyncStatus(BaseModel):
    chart_month: str
    synced: bool
    books_count: int


class ChartBook(BaseModel):
    id: str
    url: str
    title: str = Field(min_length=1)
    authors: str | None = None
    pub_date: str | None = None
    publisher: str | None = None
    list_price: str | None = None
    binding: str | None = None
    raw_info: str | None = None
    rank: int = Field(ge=1, le=1000)
    subcat: str | None = None
    months_on_chart: int | None = Field(default=None, ge=1)
    rating: float | None = Field(default=None, ge=0, le=10)
    rating_count: int | None = Field(default=None, ge=0)
    paper_price: float | None = Field(default=None, ge=0)
    paper_url: str | None = None
    ebook_url: str | None = None

    @field_validator('id')
    @classmethod
    def valid_id(cls, value: str):
        if not value.isdigit():
            raise ValueError('Douban book ID must contain only digits')
        return value


class ChartBatch(BaseModel):
    chart_month: str
    updated_at: str
    source_url: str
    pages_read: int = Field(ge=1, le=5)
    books: list[ChartBook] = Field(min_length=1, max_length=100)

    @field_validator('chart_month')
    @classmethod
    def valid_month(cls, value: str):
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', value):
            raise ValueError('Expected YYYY-MM')
        return value

    @field_validator('updated_at')
    @classmethod
    def valid_date(cls, value: str):
        datetime.strptime(value, '%Y-%m-%d')
        return value


class LatestBook(BaseModel):
    id: str
    url: str
    title: str = Field(min_length=1)
    authors: str | None = None
    pub_date: str | None = None
    publisher: str | None = None
    list_price: str | None = None
    binding: str | None = None
    raw_info: str | None = None
    rating: float | None = Field(default=None, ge=0, le=10)
    rating_count: int | None = Field(default=None, ge=0)
    paper_price: float | None = Field(default=None, ge=0)
    paper_url: str | None = None
    ebook_url: str | None = None

    @field_validator('id')
    @classmethod
    def valid_id(cls, value: str) -> str:
        if not re.fullmatch(r'\d+', value):
            raise ValueError('Book ID must consist of digits')
        return value


class LatestBatch(BaseModel):
    source_url: str
    pages_read: int = Field(ge=1, le=20)
    books: list[LatestBook] = Field(min_length=1, max_length=500)
