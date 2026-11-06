# coding=utf-8
from pydantic import BaseModel, Field, ConfigDict


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


class FirefoxDownload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_id: str = Field(min_length=1)
    download_id: int = Field(alias='id')

    url: str
    final_url: str | None = Field(default=None, alias='finalUrl')
    referrer: str | None = None
    filename: str | None = None
    mime: str | None = None

    start_time: str | None = Field(default=None, alias='startTime')
    end_time: str | None = Field(default=None, alias='endTime')

    state: str
    total_bytes: int | None = Field(default=None, alias='totalBytes')
    bytes_received: int | None = Field(default=None, alias='bytesReceived')
    exists_on_disk: bool | None = Field(default=None, alias='exists')
    error: str | None = None


class FirefoxDownloadBatch(BaseModel):
    items: list[FirefoxDownload]


class FirefoxDownloadSyncResult(BaseModel):
    count: int

