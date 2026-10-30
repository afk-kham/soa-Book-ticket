"""Entry point FastAPI của Notification Service (cổng 5006).

Chạy local:  uvicorn app.main:app --host 0.0.0.0 --port 5006
Tạo bảng (bước tường minh, không tự chạy khi khởi động):  python -m app.db.init_db [--seed]

Theo D-07: CORS tự viết (OPTIONS -> 204, Allow-Origin *) và mọi lỗi (400/404/405/413/500) trả envelope
{"status":"error","code","message"}; không lộ chi tiết lỗi nội bộ.
"""
import logging

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core import config
from app.core.errors import ApiError, error_response

logger = logging.getLogger("notification")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}

app = FastAPI(title="Notification Service", version="1.0.0")  # Swagger UI: /docs
app.router.redirect_slashes = False  # "/api/notify/" phải là 404, không chuyển hướng 307


@app.middleware("http")
async def cors_and_log(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response(status_code=204)
    else:
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Lỗi không mong đợi")
            response = error_response(500, "Lỗi nội bộ")
    response.headers.update(CORS_HEADERS)
    logger.info("method=%s path=%r status=%d", request.method, request.url.path, response.status_code)
    return response


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError):
    return error_response(exc.status, exc.message)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return error_response(404, "Không tìm thấy endpoint")
    if exc.status_code == 405:
        return error_response(405, "Phương thức không được hỗ trợ", dict(exc.headers or {}))
    return error_response(exc.status_code, "Yêu cầu không hợp lệ" if exc.status_code < 500 else "Lỗi nội bộ")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, __: RequestValidationError):
    return error_response(400, "Yêu cầu không hợp lệ")


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT)
