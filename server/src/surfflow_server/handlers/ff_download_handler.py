# coding=utf-8
from surfflow_server.config import SURFFLOW_DB
from surfflow_server.data_access.database import connect_db
from surfflow_server.data_access.firefox_download import list_downloads, upsert_downloads
from surfflow_server.schemas import FirefoxDownload


def list_ff_downloads(
        source_id: str | None = None,
        limit: int = 100,
        offset: int = 0
):
    with connect_db(SURFFLOW_DB) as db_conn:
        return list_downloads(db_conn, source_id, limit, offset)


def save_ff_downloads(req: list[FirefoxDownload]):
    with connect_db(SURFFLOW_DB) as db_conn:
        return upsert_downloads(db_conn, req)


if __name__ == '__main__':
    print(list_ff_downloads())
