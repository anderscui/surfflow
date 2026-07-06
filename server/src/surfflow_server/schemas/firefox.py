# coding=utf-8
from pydantic import BaseModel


class FirefoxHistoryItem(BaseModel):
    id: str
    url: str
    title: str | None = None

    lastVisitTime: int | None = None
    visitCount: int | None = None


class FirefoxHistorySyncRequest(BaseModel):
    start_time: int
    end_time: int
    items: list[FirefoxHistoryItem]


class FirefoxHistorySyncResponse(BaseModel):
    sync_id: int

    start_time: int
    end_time: int

    item_count: int


class OperationLogRequest(BaseModel):
    action: str
    page_url: str | None = None
    page_title: str | None = None
    context: dict | None = None


class OperationLogResponse(BaseModel):
    id: int
