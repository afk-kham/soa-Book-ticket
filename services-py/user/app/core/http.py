"""Hạ tầng HTTP của riêng User Service: envelope, CORS/OPTIONS, exception handler.

Xử lý D-07 TRONG PHẠM VI User Service (nhóm trưởng sẽ chốt mẫu dùng chung; khi có thì thay file này):
  (a) ``OPTIONS`` -> 204 (CORSMiddleware của Starlette trả 200 nên không dùng),
  (b) lỗi validation 422/``detail`` -> 400 ``VALIDATION_ERROR`` đúng envelope,
  (c) 404/405/500 -> envelope ``{"status":"error","code","message"}``,
  (d) không bao giờ lộ lỗi SQL, stack trace, mật khẩu hay hash.
"""
import logging
import sqlite3
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

logger = logging.getLogger("user-service")

JSON_MEDIA_TYPE = "application/json; charset=utf-8"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "3600",
}

_CODE_BY_STATUS = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
}


class EnvelopeResponse(JSONResponse):
    media_type = JSON_MEDIA_TYPE


def success(status_code: int, data: Any) -> EnvelopeResponse:
    return EnvelopeResponse(status_code=status_code, content={"status": "success", "data": data})


def error(status_code: int, message: str, code: str | None = None, headers: dict | None = None) -> EnvelopeResponse:
    code = code or _CODE_BY_STATUS.get(status_code, "INTERNAL_ERROR" if status_code >= 500 else "ERROR")
    return EnvelopeResponse(
        status_code=status_code,
        content={"status": "error", "code": code, "message": message},
        headers=headers,
    )


def validation_message(errors: list[dict]) -> str:
    """Chọn thông báo tiếng Việt từ lỗi validation đầu tiên. KHÔNG lặp lại giá trị client gửi."""
    first = errors[0] if errors else {}
    etype = first.get("type", "")
    loc = tuple(first.get("loc", ()))
    if etype == "value_error":
        ctx_error = (first.get("ctx") or {}).get("error")
        if ctx_error is not None:
            return str(ctx_error)
    if etype == "json_invalid":
        return "JSON không hợp lệ"
    if loc == ("body",) or etype in {"model_attributes_type", "dict_type", "model_type"}:
        return "Body phải là đối tượng JSON"
    if loc and loc[0] == "query":
        return f"Tham số {loc[-1]} không hợp lệ"
    return "Dữ liệu không hợp lệ"


def register_http_handling(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        return error(400, validation_message(exc.errors()))

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return error(404, f"Không tìm thấy đường dẫn: {request.url.path}")
        if exc.status_code == 405:
            return error(405, "Phương thức không được hỗ trợ cho đường dẫn này", headers=dict(exc.headers or {}))
        return error(exc.status_code, "Yêu cầu không hợp lệ" if exc.status_code < 500 else "Lỗi máy chủ")

    @app.middleware("http")
    async def _cors_and_safety_net(request: Request, call_next):
        if request.method == "OPTIONS":  # preflight: luôn 204 theo hợp đồng
            return Response(status_code=204, headers=CORS_HEADERS)
        try:
            response = await call_next(request)
        except sqlite3.Error as exc:
            logger.error("DB error: %s", type(exc).__name__)  # chỉ ghi tên lỗi, không ghi nội dung
            response = error(500, "Lỗi cơ sở dữ liệu")
        except Exception as exc:  # noqa: BLE001 - lưới an toàn cuối cùng, không lộ chi tiết
            logger.error("Unhandled error: %s", type(exc).__name__)
            response = error(500, "Lỗi máy chủ")
        for key, value in CORS_HEADERS.items():
            response.headers[key] = value
        return response
