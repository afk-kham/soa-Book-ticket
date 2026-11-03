"""Controller: đọc request -> kiểm tra đầu vào -> gọi Service -> dựng envelope + mã HTTP. Không viết SQL."""
import json
import re

from fastapi import Request
from pydantic import BaseModel, ValidationError

from app.core import config
from app.core.errors import BookingError, validation_error
from app.core.http import EnvelopeResponse, error, success
from app.core.jwt_auth import verify_bearer
from app.entities import BOOKING_STATUSES, MAX_ID
from app.schemas import (
    BookingResponse,
    BookingResultResponse,
    CancelBookingRequest,
    CreateBookingRequest,
    PayBookingRequest,
)
from app.services import BookingService

MAX_BODY_BYTES = 64 * 1024
MAX_AVAILABILITY_IDS = 500
ADMIN_ROLE = "ADMIN"

_INT_RE = re.compile(r"\+?[0-9]+")

_HTTP_STATUS = {
    "VALIDATION_ERROR": 400,
    "SHOWTIME_CLOSED": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "USER_NOT_FOUND": 404,
    "MOVIE_NOT_FOUND": 404,
    "SHOWTIME_NOT_FOUND": 404,
    "SEAT_TAKEN": 409,
    "ALREADY_PAID": 409,
    "BOOKING_CANCELLED": 409,
    "PAID_NOT_CANCELLABLE": 409,
    "PAYLOAD_TOO_LARGE": 413,
}


def _http_status(code: str) -> int:
    if code.endswith("_SERVICE_ERROR"):
        return 502
    if code.endswith("_SERVICE_UNAVAILABLE"):
        return 503
    return _HTTP_STATUS.get(code, 500)


async def handle_booking_error(_: Request, exc: BookingError) -> EnvelopeResponse:
    return error(_http_status(exc.code), exc.code, exc.message)


def _reject_json_constant(name: str) -> None:
    raise ValueError(f"{name} không phải JSON hợp lệ")


async def _read_json(request: Request) -> dict:
    """Đọc body JSON object; dừng ngay khi vượt 64 KiB. Không bao giờ crash vì body rỗng hoặc sai."""
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            raise BookingError("PAYLOAD_TOO_LARGE", "Body quá lớn")
        chunks.append(chunk)
    if size == 0:
        raise validation_error("Body yêu cầu rỗng")
    try:
        body = json.loads(b"".join(chunks), parse_constant=_reject_json_constant)
    except (ValueError, RecursionError) as exc:
        raise validation_error("JSON không hợp lệ") from exc
    if not isinstance(body, dict):
        raise validation_error("Body phải là một đối tượng JSON")
    return body


def _validated[T: BaseModel](model: type[T], data: dict) -> T:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        reason = exc.errors()[0].get("ctx", {}).get("error")
        raise validation_error(str(reason or "Dữ liệu yêu cầu không hợp lệ")) from exc


def _parse_positive_int(raw: str | None) -> int | None:
    """Số nguyên dương 32 bit (như int.TryParse của mã cũ); sai -> None."""
    text = (raw or "").strip()
    if not _INT_RE.fullmatch(text) or not 0 < int(text) <= MAX_ID:
        return None
    return int(text)


def _identity(request: Request) -> dict | None:
    """Claims JWT khi bật JWT_REQUIRED; tắt thì trả None và danh tính lấy từ body như baseline."""
    return verify_bearer(request.headers.get("authorization")) if config.JWT_REQUIRED else None


def _is_admin(claims: dict | None) -> bool:
    return claims is not None and claims.get("role") == ADMIN_ROLE


class BookingController:
    def __init__(self, service: BookingService):
        self._service = service

    def health(self) -> EnvelopeResponse:
        self._service.ping()
        return success(200, {"service": config.SERVICE_NAME, "port": config.PORT})

    async def create(self, request: Request) -> EnvelopeResponse:
        claims = _identity(request)
        data = await _read_json(request)
        if claims:
            data["username"] = claims["sub"]  # không tin body
        body = _validated(CreateBookingRequest, data)
        result = await self._service.create_booking(
            body.username,
            body.movie_id,
            body.showtime_id,
            body.seats,
            body.payment_method,
            body.pay_now,
            request.headers.get("authorization"),
        )
        return success(201, BookingResultResponse.from_result(result).model_dump(by_alias=True))

    async def pay(self, request: Request, booking_id: int) -> EnvelopeResponse:
        claims = _identity(request)
        data = await _read_json(request)
        if claims:
            data["username"] = claims["sub"]
        body = _validated(PayBookingRequest, data)
        result = await self._service.pay_booking(
            booking_id, body.username, body.payment_method, _is_admin(claims), request.headers.get("authorization")
        )
        return success(200, BookingResultResponse.from_result(result).model_dump(by_alias=True))

    async def cancel(self, request: Request, booking_id: int) -> EnvelopeResponse:
        claims = _identity(request)
        data = await _read_json(request)
        if claims:
            data["username"] = claims["sub"]
        body = _validated(CancelBookingRequest, data)
        result = self._service.cancel_booking(booking_id, body.username, _is_admin(claims))
        return success(200, BookingResultResponse.from_result(result).model_dump(by_alias=True))

    def list_bookings(
        self, request: Request, username: str | None, status: str | None, showtime_id: str | None
    ) -> EnvelopeResponse:
        claims = _identity(request)
        parsed_showtime_id = None
        if showtime_id:
            parsed_showtime_id = _parse_positive_int(showtime_id)
            if parsed_showtime_id is None:
                raise validation_error("showtimeId phải là số nguyên dương")
        status = status.upper() if status is not None else None
        if status is not None and status not in BOOKING_STATUSES:
            raise validation_error("status chỉ nhận PENDING, PAID hoặc CANCELLED")
        username = username if username and username.strip() else None
        # "Vé của tôi" của Client dùng chính endpoint này: USER chỉ được xem đơn của mình
        if claims and not _is_admin(claims) and username != claims["sub"]:
            raise BookingError("FORBIDDEN", "Bạn không có quyền xem danh sách đơn này")
        bookings = self._service.list_bookings(username, status, parsed_showtime_id)
        return success(200, [BookingResponse.from_entity(b).model_dump(by_alias=True) for b in bookings])

    def get(self, request: Request, booking_id: int) -> EnvelopeResponse:
        claims = _identity(request)
        booking = self._service.get_booking(booking_id, claims["sub"] if claims else None, _is_admin(claims))
        return success(200, BookingResponse.from_entity(booking).model_dump(by_alias=True))

    def seats(self, showtime_id: str | None) -> EnvelopeResponse:
        parsed = _parse_positive_int(showtime_id)
        if parsed is None:
            raise validation_error("showtimeId là bắt buộc (số nguyên dương)")
        return success(200, {"showtimeId": parsed, "seats": self._service.taken_seats(parsed)})

    def availability(self, showtime_ids: str | None) -> EnvelopeResponse:
        ids = []
        for part in filter(None, (piece.strip() for piece in (showtime_ids or "").split(","))):
            parsed = _parse_positive_int(part)
            if parsed is None:
                raise validation_error("showtimeIds là danh sách số nguyên dương, ví dụ 1,2,3")
            ids.append(parsed)
        if not 1 <= len(ids) <= MAX_AVAILABILITY_IDS:
            raise validation_error("showtimeIds cần từ 1 đến 500 suất chiếu")
        counts = self._service.availability(ids)
        return success(200, [{"showtimeId": sid, "taken": taken} for sid, taken in counts.items()])
