# coding=utf-8
from surfflow_server.config import SURFFLOW_DB
from surfflow_server.data_access.database import connect_db
from surfflow_server.data_access.firefox_history import get_last_history_sync_time, save_sync_op
from surfflow_server.schemas import FirefoxHistorySyncRequest, FirefoxHistorySyncResponse


def get_last_hist_sync_time():
    db_conn = connect_db(SURFFLOW_DB)
    return get_last_history_sync_time(db_conn)


def save_ff_history_sync(req: FirefoxHistorySyncRequest):
    db_conn = connect_db(SURFFLOW_DB)
    sync_id = save_sync_op(db_conn, req)
    return FirefoxHistorySyncResponse(
        sync_id=sync_id,
        start_time=req.start_time,
        end_time=req.end_time,
        item_count=len(req.items)
    )


if __name__ == '__main__':
    print(get_last_hist_sync_time())
