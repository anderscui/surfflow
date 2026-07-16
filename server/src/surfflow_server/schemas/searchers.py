# coding=utf-8
from pathlib import Path

import datetime

import humanize
from pydantic import BaseModel, Field
from dateutil.parser import parse

from surfflow_server.schemas.files import FileInfo, parse_storage_type, SizeLabels, FileTypes


class SearchResult(BaseModel):
    source: str
    raw_path: str
    score: float| None = None
    rank: int | None = None
    matched_text: str | None = None
    metadata: dict | None = None


class SearchedFileInfo(BaseModel):
    id: str

    score: float
    relevance_score: float

    # base_dir: str
    raw_path: str
    parent_path: str = ''
    name: str
    stem: str
    extension: str
    size: int
    page_count: int | None = None

    creation_datetime: datetime.datetime | None = None
    modification_datetime: datetime.datetime | None = None
    last_access_datetime: datetime.datetime | None = None

    creation_date: str | None = None
    modification_date: str | None = None
    last_access_date: str | None = None

    hash: str | None = None
    tags: list[str] = Field(default_factory=list)

    outline_titles: list[str] = Field(default_factory=list)

    file_size: str | None = None
    size_label: str | None = None
    file_type: str | None = None
    storage_type: str | None = None
    collection: str | None = None

    local_url: str | None = None
    search_type: str | None = None

    @classmethod
    def load_obj(cls, obj: dict | FileInfo):
        def set_datetime_field(time_field_name):
            datetime_field_name = time_field_name.replace('_time', '_datetime')
            date_field_name = time_field_name.replace('_time', '_date')

            time_field = obj.get(time_field_name) or None
            if isinstance(time_field, str):
                datetime_field = parse(time_field)
                date_field = humanize.naturaldate(datetime_field)
                time_field = datetime_field.timestamp()
                obj.update({
                    datetime_field_name: datetime_field,
                    date_field_name: date_field,
                    time_field_name: time_field,
                })

        if isinstance(obj, FileInfo):
            obj = obj.model_dump(mode='json')
        else:
            obj = dict(obj)

        set_datetime_field('creation_time')
        set_datetime_field('modification_time')
        set_datetime_field('last_access_time')

        file_type = obj['file_type']
        raw_path = obj['raw_path']
        obj['storage_type'] = parse_storage_type(raw_path)
        file_size = obj['size']
        if file_size is not None:
            obj['file_size'] = humanize.naturalsize(file_size)
            obj['size_label'] = SizeLabels.parse(file_type, file_size)

        local_url = None
        if file_type in (FileTypes.book, FileTypes.video, FileTypes.image, FileTypes.audio):
            local_url = Path(raw_path).as_uri()
        obj['local_url'] = local_url

        return cls.model_validate(obj)


class SearchedFileResult(BaseModel):
    total: int
    num_hits: int

    max_score: float | None = None
    hits: list[SearchedFileInfo] = Field(default_factory=list)

    # @property
    # def num_hits(self):
    #     return len(self.hits)
