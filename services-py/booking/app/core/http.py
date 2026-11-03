"""Hạ tầng HTTP của riêng Booking Service: envelope, CORS/OPTIONS, exception handler.

Xử lý D-07 TRONG PHẠM VI service (nhóm trưởng chốt mẫu dùng chung thì thay file này):
  (a) ``OPTIONS`` -> 204 không có body (CORSMiddleware của Starlette trả 200 nên không dùng),
  (b) 404/405/500 -> envelope ``{"status":"error","code","message"}``,
  (c) không bao giờ lộ lỗi SQL hay stack trace.
"""
import logging
import sqlite3
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.routing import Match

logger = logging.getLogger("booking-service")

JSON_MEDIA_TYPE = "application/json; charset=utf-8"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "3600",
}


class EnvelopeResponse(JSONResponse):
    media_type = JSON_MEDIA_TYPE


def success(status_code: int, data: Any) -> EnvelopeResponse:
    return EnvelopeResponse(status_code=status_code, content={"status": "success", "data": data})


def error(status_code: int, code: str, message: str, headers: dict | None = None) -> EnvelopeResponse:
    return EnvelopeResponse(
        status_code=status_code,
        content={"status": "error", "code": code, "message": message},
        headers=headers,
    )


def _allowed_methods(router: APIRouter, request: Request) -> str:
    """Mọi method của path này. Starlette chỉ báo route khớp đầu tiên, thiếu khi một path có nhiều route."""
    methods = {"OPTIONS"}
    for route in router.routes:
        if route.matches(request.scope)[0] is not Match.NONE:
            methods |= route.methods
    return ", ".join(sorted(methods))


def register_http_handling(app: FastAPI, router: APIRouter) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        return error(400, "VALIDATION_ERROR", "Dữ liệu yêu cầu không hợp lệ")

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return error(404, "NOT_FOUND", "Endpoint không tồn tại")
        if exc.status_code == 405:
            return error(
                405,
                "METHOD_NOT_ALLOWED",
                "Phương thức không được hỗ trợ trên endpoint này",
                headers={"Allow": _allowed_methods(router, request)},
            )
        return error(exc.status_code, "INTERNAL_ERROR", "Lỗi máy chủ nội bộ")

    @app.middleware("http")
    async def _cors_and_safety_net(request: Request, call_next):
        if request.method == "OPTIONS":  # preflight: luôn 204 theo hợp đồng
            return Response(status_code=204, headers=CORS_HEADERS)
        request.scope["path"] = request.scope["path"].rstrip("/") or "/"  # như TrimEnd('/') của mã cũ
        try:
            response = await call_next(request)
        except sqlite3.Error as exc:
            logger.error("DB error: %s", type(exc).__name__)  # chỉ ghi tên lỗi, không ghi nội dung
            response = error(500, "INTERNAL_ERROR", "Lỗi máy chủ nội bộ")
        except Exception:  # noqa: BLE001 - lưới an toàn cuối cùng, chi tiết chỉ nằm trong log
            logger.exception("Lỗi không mong đợi")
            response = error(500, "INTERNAL_ERROR", "Lỗi máy chủ nội bộ")
        for key, value in CORS_HEADERS.items():
            response.headers[key] = value
        return response
