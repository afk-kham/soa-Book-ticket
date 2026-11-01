"""Entry point FastAPI của Movie Service (cổng 5001).

Chạy local:
  uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload

Swagger UI:
  http://localhost:5001/docs
OpenAPI JSON:
  http://localhost:5001/openapi.json
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core import config
from app.core.http import register_http_handling
from app.db import init_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Vòng đời của Movie Service: Tự động khởi tạo schema khi app bắt đầu chạy."""
    init_schema()
    yield


tags_metadata = [
    {
        "name": "Health",
        "description": "Kiểm tra tình trạng hoạt động và cổng dịch vụ (dùng cho giám sát & Docker Healthcheck).",
    },
    {
        "name": "Movies",
        "description": "Quản lý danh mục phim: truy vấn danh sách, xem chi tiết, thêm mới, sửa và xóa phim.",
    },
]

app = FastAPI(
    title="Movie Service API (TV1)",
    description="Dịch vụ quản lý danh mục phim - Kiến trúc SOA (Nhánh TV1)",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

register_http_handling(app)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT)
