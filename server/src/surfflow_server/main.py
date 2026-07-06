# coding=utf-8
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from surfflow_server.handlers.book_handler import extract_book_titles
from surfflow_server.handlers.ff_history_handler import get_last_hist_sync_time, save_ff_history_sync
from surfflow_server.handlers.operation_log_handler import save_operation_log
from surfflow_server.schemas import ExtractBookRequest, FirefoxHistorySyncRequest
from surfflow_server.schemas import OperationLogResponse, OperationLogRequest


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
    print(req.start_time, req.end_time, f'{len(req.items)} items:')
    for item in req.items[:5]:
        print(item)
    return save_ff_history_sync(req)


@app.post(
    "/api/v1/operations/log",
    response_model=OperationLogResponse,
)
async def log_operation(req: OperationLogRequest):
    log_id = save_operation_log(req)
    return OperationLogResponse(id=log_id)


def run() -> None:
    uvicorn.run(
        "surfflow_server.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == '__main__':
    run()
