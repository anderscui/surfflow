# coding=utf-8
import re
import subprocess
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Query, Header, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from archaeo.io.files import get_absolute_path, is_relative_to_any
from surfflow_server.config import SOURCE_DIRS, logger
from surfflow_server.handlers.book_handler import extract_book_titles
from surfflow_server.handlers.douban_book_handler import get_chart_sync_status, save_book_chart, save_book_latest_batch
from surfflow_server.handlers.ff_download_handler import save_ff_downloads, list_ff_downloads
from surfflow_server.handlers.ff_history_handler import get_last_hist_sync_time, save_ff_history_sync
from surfflow_server.handlers.operation_log_handler import save_operation_log
from surfflow_server.schemas import ExtractBookRequest, FirefoxHistorySyncRequest, ChartBatch, LatestBatch
from surfflow_server.schemas import FirefoxDownloadSyncResult, FirefoxDownloadBatch, FirefoxDownload
from surfflow_server.schemas import OperationLogResponse, OperationLogRequest
from surfflow_server.schemas.local_finder import FileActionRequest, FileAction
from surfflow_server.searchers import get_default_local_file_searcher

router_db_book_chart = APIRouter(prefix='/api/v1/douban/book_chart', tags=['douban-book-chart'])
router_db_book_latest = APIRouter(prefix='/api/v1/douban/book_latest', tags=['douban-book-latest'])

def create_app() -> FastAPI:
    app = FastAPI(title="SurfFlow Server", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://127.0.0.1",
            "moz-extension://*",  # 这个未必总能按预期匹配
        ],
        allow_origin_regex=r"moz-extension://.*",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # @app.on_event("startup")
    # def on_startup() -> None:
    #     init_db()

    # app.include_router(router, prefix="/api")
    return app


app = create_app()
app.include_router(router_db_book_chart)
app.include_router(router_db_book_latest)
templates = Jinja2Templates(directory='templates')
app.mount(
    '/static',
    StaticFiles(directory='static'),
    name='static',
)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='index.html',
        context={}
    )


@app.post("/api/v1/extract/books")
async def extract_books(req: ExtractBookRequest):
    book_titles = extract_book_titles(req.text)
    return {"books": book_titles}


@app.get("/api/v1/firefox/history/last_sync_time")
async def get_ff_last_hist_sync_time():
    return {'last_sync_time': get_last_hist_sync_time()}


@app.post("/api/v1/firefox/history/sync")
async def get_ff_sync_history_items(req: FirefoxHistorySyncRequest):
    logger.debug(f'{req.start_time} -> {req.end_time}, {len(req.items)} items:')
    for item in req.items[:5]:
        logger.debug(item)
    return save_ff_history_sync(req)


@app.post(
    '/api/v1/firefox/downloads',
    response_model=FirefoxDownloadSyncResult
)
def save_download(record: FirefoxDownload):
    count = save_ff_downloads([record])
    return FirefoxDownloadSyncResult(count=count)


@app.post(
    '/api/v1/firefox/downloads/batch',
    response_model=FirefoxDownloadSyncResult
)
def save_download_batch(batch: FirefoxDownloadBatch):
    count = save_ff_downloads(batch.items)
    return FirefoxDownloadSyncResult(count=count)


@app.get('/api/v1/firefox/downloads')
def get_downloads(
    source_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    return list_ff_downloads(
        source_id=source_id,
        limit=limit,
        offset=offset,
    )


@app.post(
    "/api/v1/operations/log",
    response_model=OperationLogResponse,
)
async def log_operation(req: OperationLogRequest):
    log_id = save_operation_log(req)
    return OperationLogResponse(id=log_id)


@router_db_book_chart.get("/status")
def douban_book_chart_status(month: str):
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month):
        raise HTTPException(status_code=422, detail='Invalid chart month')
    status = get_chart_sync_status(month)
    return status


@router_db_book_chart.post('/batch')
def save_db_book_chart_batch(batch: ChartBatch):
    ids = [book.id for book in batch.books]
    ranks = [book.rank for book in batch.books]
    if len(set(ids)) != len(ids) or len(set(ranks)) != len(ranks):
        raise HTTPException(status_code=422, detail='Duplicate IDs or ranks')
    if min(ranks) != 1 or sorted(ranks) != list(range(1, max(ranks) + 1)):
        raise HTTPException(status_code=422, detail='Incomplete or non-contiguous ranking')

    logger.debug(batch.books[:5])
    result = save_book_chart(batch)
    logger.debug(result)
    return result


@router_db_book_latest.post('/batch')
def save_db_book_latest_batch(batch: LatestBatch):
    ids = [book.id for book in batch.books]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail='Repeated Douban book IDs in batch')

    logger.debug(batch.books[:5])
    result = save_book_latest_batch(batch)
    logger.debug(result)
    return result


@app.get('/search')
def search_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='search.html',
        context={}
    )


@app.get("/api/v1/files/search")
def search_file(q: str,
                n: Annotated[int, Query(ge=1, le=100)] = 10):
    searcher = get_default_local_file_searcher()
    files = searcher.search(q, limit=n)
    logger.debug(files[:5])
    return files


@app.post("/api/v1/files/action")
def local_file_actions(req: FileActionRequest):
    path = get_absolute_path(req.raw_path)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="File does not exist",
        )

    if not is_relative_to_any(path, SOURCE_DIRS):
        raise HTTPException(
            status_code=403,
            detail='File is outside configured dirs.'
        )

    match req.action:
        case FileAction.REVEAL:
            subprocess.run(["open", "-R", str(path)], check=True)
        case FileAction.OPEN:
            subprocess.run(["open", str(path)], check=True)
        case FileAction.COPY_PATH:
            return {"ok": True, 'path': str(path)}
        case FileAction.ARCHIVE:
            return {"ok": True, 'path': str(path)}

    # unknown action
    return {"ok": False}


def run() -> None:
    uvicorn.run(
        "surfflow_server.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == '__main__':
    run()
