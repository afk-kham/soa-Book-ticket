"""Entry point FastAPI của User Service (cổng 5003).

Chạy local:  uvicorn app.main:app --host 0.0.0.0 --port 5003 --reload
- Import module KHÔNG tạo file DB. Khi khởi động (lifespan) chỉ chạy ``init_schema()``
  (CREATE TABLE IF NOT EXISTS, không seed). Seed: ``python -m app.db.seed`` (tường minh).
- CORS/OPTIONS->204/envelope lỗi: xem ``app/core/http.py`` (D-07, xử lý trong phạm vi service).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core import config
from app.core.http import register_http_handling
from app.db import init_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema()
    yield


app = FastAPI(title="User Service", version="1.0.0", lifespan=lifespan, strict_content_type=False)
register_http_handling(app)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT)
