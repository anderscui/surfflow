# coding=utf-8
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from surfflow_server.handlers.book_handler import extract_book_titles
from surfflow_server.schemas import ExtractBookRequest


# from surfflow_server.api.routes import router
# from surfflow_server.database import init_db


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


@app.get("/")
async def root():
    return {"message": "Hello, SurfFlow!"}


@app.post("/api/v1/extract/books")
async def extract_books(req: ExtractBookRequest):
    book_titles = extract_book_titles(req.text)
    return {"books": book_titles}


def run() -> None:
    uvicorn.run(
        "surfflow_server.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == '__main__':
    run()
