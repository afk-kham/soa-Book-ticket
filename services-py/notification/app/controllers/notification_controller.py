"""Controller: nhận request -> kiểm tra hình dạng body -> gọi service -> dựng envelope."""
import json
import re
from typing import TypeVar

from fastapi import Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from app.core.errors import ApiError, success_response
from app.schemas.notification import (CreateLogRequest, NotifyRequest, UpdateLogRequest,
                                      log_to_dict, notify_to_dict)
from app.services.notification_service import NotificationService

MAX_BODY = 16 * 1024
_ID = re.compile(r"[0-9]+")
T = TypeVar("T", bound=BaseModel)
service = NotificationService()


async def _read_body(request: Request) -> bytes:
    """Đọc body, dừng ngay khi vượt 16 KiB (413)."""
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY:
            raise ApiError(413, "Body vượt quá 16 KiB")
        chunks.append(chunk)
    return b"".join(chunks)


async def _parse(request: Request, model: type[T]) -> T:
    body = await _read_body(request)
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ApiError(400, "Body phải là một JSON object")
    if not isinstance(data, dict):
        raise ApiError(400, "Body phải là một JSON object")
    try:
        return model.model_validate(data)
    except ValidationError:
        raise ApiError(400, "JSON không hợp lệ hoặc có trường không được hỗ trợ")


def _parse_id(raw: str) -> int:
    if not _ID.fullmatch(raw) or int(raw) <= 0 or int(raw) > 9223372036854775807:
        raise ApiError(400, "ID phải là số nguyên dương")
    return int(raw)


async def notify(request: Request) -> JSONResponse:
    n = service.notify(await _parse(request, NotifyRequest))
    return success_response(notify_to_dict(n))


async def list_logs(bookingId: str | None = Query(None, description="Lọc theo mã đơn"),
                    username: str | None = Query(None, description="Lọc theo tên (không phân biệt hoa thường)"),
                    channel: str | None = Query(None, description="EMAIL hoặc SMS")) -> JSONResponse:
    logs = service.list_logs(bookingId, username, channel)
    return success_response([log_to_dict(n) for n in logs])


async def list_all() -> JSONResponse:
    """GET / : toàn bộ nhật ký hiện có (mới nhất trước), cùng dạng với GET /api/notify/logs."""
    return success_response([log_to_dict(n) for n in service.list_logs(None, None, None)])


async def create_log(request: Request) -> JSONResponse:
    n = service.create_log(await _parse(request, CreateLogRequest))
    return success_response(log_to_dict(n), 201)


async def get_log(log_id: str) -> JSONResponse:
    return success_response(log_to_dict(service.get_log(_parse_id(log_id))))


async def update_log(log_id: str, request: Request) -> JSONResponse:
    lid = _parse_id(log_id)
    n = service.update_log(lid, await _parse(request, UpdateLogRequest))
    return success_response(log_to_dict(n))


async def delete_log(log_id: str) -> JSONResponse:
    lid = _parse_id(log_id)
    service.delete_log(lid)
    return success_response({"id": lid, "deleted": True, "message": "Đã xóa nhật ký thông báo thành công"})
