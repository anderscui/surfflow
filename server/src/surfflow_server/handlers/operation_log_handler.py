# coding=utf-8
from surfflow_server.config import SURFFLOW_DB
from surfflow_server.data_access.database import connect_db
from surfflow_server.data_access.operation_log import insert_operation_log
from surfflow_server.schemas import OperationLogRequest


def save_operation_log(req: OperationLogRequest):
    conn = connect_db(SURFFLOW_DB)

    try:
        log_id = insert_operation_log(conn, req)
        return log_id
    finally:
        conn.close()
