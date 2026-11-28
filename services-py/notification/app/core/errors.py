"""Lỗi nghiệp vụ + envelope dùng chung cho service (xem D-07)."""
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status: int, message: str, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code


def error_code(status: int) -> str:
    if status == 400:
        return "VALIDATION_ERROR"
    if status == 404:
        return "NOT_FOUND"
    if status == 405:
        return "METHOD_NOT_ALLOWED"
    if status == 413:
        return "PAYLOAD_TOO_LARGE"
    if status >= 500:
        return "INTERNAL_ERROR"
    return "ERROR"


def error_response(status: int, message: str, headers: dict | None = None, code: str | None = None) -> JSONResponse:
    return JSONResponse(
        {"status": "error", "code": code or error_code(status), "message": message},
        status_code=status,
        headers=headers,
    )


def success_response(data, status: int = 200) -> JSONResponse:
    return JSONResponse({"status": "success", "data": data}, status_code=status)
