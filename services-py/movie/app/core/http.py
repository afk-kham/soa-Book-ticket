"""Hạ tầng HTTP của Movie Service: envelope chuẩn, CORS/OPTIONS, exception handling.

Tuân thủ nghiêm ngặt API_CONTRACT.md:
  (a) OPTIONS -> 204 No Content
  (b) Lỗi validation (Pydantic / RequestValidationError) -> 400 VALIDATION_ERROR với message tiếng Việt
  (c) Lỗi 404/405/500 -> envelope {"status": "error", "code": "...", "message": "..."}
  (d) Thành công -> envelope {"status": "success", "data": ...}
  (e) Không để lộ stack trace hay chi tiết nội bộ CSDL
"""
import logging
import sqlite3
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

logger = logging.getLogger("movie-service")

JSON_MEDIA_TYPE = "application/json; charset=utf-8"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
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
    """Trả response thành công theo envelope chuẩn: {"status": "success", "data": ...}"""
    return EnvelopeResponse(status_code=status_code, content={"status": "success", "data": data})


def error(status_code: int, message: str, code: str | None = None, headers: dict | None = None) -> EnvelopeResponse:
    """Trả response lỗi theo envelope chuẩn: {"status": "error", "code": "...", "message": "..."}"""
    code = code or _CODE_BY_STATUS.get(status_code, "INTERNAL_ERROR" if status_code >= 500 else "ERROR")
    return EnvelopeResponse(
        status_code=status_code,
        content={"status": "error", "code": code, "message": message},
        headers=headers,
    )


def validation_message(errors: list[dict]) -> str:
    """Rút gọn thông báo lỗi validation Pydantic thành tiếng Việt dễ hiểu."""
    if not errors:
        return "Dữ liệu không hợp lệ"
    first = errors[0]
    etype = first.get("type", "")
    loc = tuple(first.get("loc", ()))

    if etype == "value_error":
        ctx_error = (first.get("ctx") or {}).get("error")
        if ctx_error is not None:
            return str(ctx_error)
    if etype == "json_invalid":
        return "Định dạng JSON không hợp lệ"
    if loc == ("body",) or etype in {"model_attributes_type", "dict_type", "model_type"}:
        return "Body phải là một đối tượng JSON"
    if "title" in loc:
        return "Trường 'title' là bắt buộc và không được để trống"
    if "duration" in loc:
        return "Thời lượng phim ('duration') phải là số nguyên lớn hơn 0"
    return "Dữ liệu không hợp lệ"


def register_http_handling(app: FastAPI) -> None:
    """Đăng ký middleware CORS, preflight OPTIONS 204 và các exception handler chuẩn envelope."""

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_request: Request, exc: RequestValidationError):
        return error(400, validation_message(exc.errors()), code="VALIDATION_ERROR")

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return error(404, f"Không tìm thấy endpoint: {request.url.path}", code="NOT_FOUND")
        if exc.status_code == 405:
            return error(405, "Phương thức không được hỗ trợ trên endpoint này", code="METHOD_NOT_ALLOWED", headers=dict(exc.headers or {}))
        return error(exc.status_code, "Yêu cầu không hợp lệ" if exc.status_code < 500 else "Lỗi máy chủ nội bộ")

    @app.middleware("http")
    async def _cors_and_safety_net(request: Request, call_next):
        if request.method == "OPTIONS":
            return Response(status_code=204, headers=CORS_HEADERS)
        try:
            response = await call_next(request)
        except sqlite3.Error as exc:
            logger.error("DB error: %s", type(exc).__name__)
            response = error(500, "Lỗi cơ sở dữ liệu", code="INTERNAL_ERROR")
        except Exception as exc:  # noqa: BLE001
            logger.error("Unhandled error: %s: %s", type(exc).__name__, exc)
            response = error(500, "Lỗi máy chủ nội bộ", code="INTERNAL_ERROR")

        for key, value in CORS_HEADERS.items():
            response.headers[key] = value
        return response

