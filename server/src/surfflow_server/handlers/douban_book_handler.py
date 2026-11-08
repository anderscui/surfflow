# coding=utf-8
from surfflow_server.config import SURFFLOW_DB
from surfflow_server.data_access.database import connect_db
from surfflow_server.data_access.douban_book import get_book_chart_sync_status, save_chart
from surfflow_server.schemas import ChartBatch, ChartBook


def get_chart_sync_status(month: str):
    with connect_db(SURFFLOW_DB) as db_conn:
        return get_book_chart_sync_status(db_conn, month)


def save_book_chart(batch: ChartBatch):
    with connect_db(SURFFLOW_DB) as db_conn:
        return save_chart(db_conn, batch)


if __name__ == '__main__':
    print(get_chart_sync_status('2026-10'))

    result = save_book_chart(ChartBatch(chart_month='2026-10',
                               updated_at='2026-11-02',
                               source_url='https://book.douban.com/chart?subcat=all&updated_at=2026-11-02',
                               pages_read=3,
                               books=[ChartBook(id="12345678",
                                                title="Example Book",
                                                rank=1,
                                                subcat="文学",
                                                months_on_chart=3,
                                                url="https://book.douban.com/chart?")
                                      ]
                               ))
    print(result)
