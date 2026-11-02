"""Pydantic request/response (camelCase theo API_CONTRACT §5).

Request: kiểm tra theo đúng thứ tự và đúng thông báo lỗi của Program.cs. Trường sai kiểu được coi như
vắng mặt, trường lạ bị bỏ qua, nên body do Client/Admin đang gửi vẫn được nhận như mã cũ.
"""
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from app.entities import MAX_ID, Booking, BookingResult, PaymentOutcome

SEAT_RE = re.compile(r"[A-Z][0-9]{1,2}")
MAX_SEATS = 10
MAX_USERNAME_LENGTH = 50
DEFAULT_PAYMENT_METHOD = "MOMO"


class _Schema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


def _text(raw: dict, key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) else None


def _payment_method(raw: dict, default: str) -> str:
    """paymentMethod, hoặc tên cũ method, hoặc giá trị mặc định; chuẩn hóa chữ hoa."""
    value = _text(raw, "paymentMethod")
    if value is None:
        value = _text(raw, "method")
    if value is None:
        value = default
    return value.strip().upper()


def _positive_int(raw: dict, key: str) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= MAX_ID:
        raise ValueError(f"{key} là bắt buộc và phải là số nguyên dương")
    return value


def _seats(raw: dict) -> list[str]:
    value = raw.get("seats")
    if not isinstance(value, list):
        raise ValueError('seats là bắt buộc, ví dụ ["A1","A2"]')
    seats = []
    for item in value:
        seat = item.strip().upper() if isinstance(item, str) else ""
        if not SEAT_RE.fullmatch(seat):
            raise ValueError("Mã ghế không hợp lệ (ví dụ A1, B12)")
        seats.append(seat)
    if not 1 <= len(seats) <= MAX_SEATS:
        raise ValueError("Mỗi đơn đặt từ 1 đến 10 ghế")
    if len(set(seats)) != len(seats):
        raise ValueError("Danh sách ghế bị trùng")
    return seats


def _owner(raw: dict) -> str:
    username = (_text(raw, "username") or "").strip()
    if not username:
        raise ValueError("username là bắt buộc")
    return username


class CreateBookingRequest(_Schema):
    username: str = Field(description="Bỏ qua khi bật JWT_REQUIRED: lấy từ token")
    movie_id: int
    showtime_id: int
    seats: list[str] = Field(description='1-10 ghế dạng A1, B12, không trùng, ví dụ ["A5","A6"]')
    payment_method: str = Field(default=DEFAULT_PAYMENT_METHOD, description="Nhận cả tên cũ `method`")
    pay_now: bool = Field(default=True, description="false: chỉ giữ ghế, thanh toán sau qua /pay")

    @model_validator(mode="before")
    @classmethod
    def _check(cls, raw: dict) -> dict:
        username = (_text(raw, "username") or "").strip()
        if not username or len(username) > MAX_USERNAME_LENGTH:
            raise ValueError("username là bắt buộc (tối đa 50 ký tự)")
        return {
            "username": username,
            "movieId": _positive_int(raw, "movieId"),
            "showtimeId": _positive_int(raw, "showtimeId"),
            "seats": _seats(raw),
            "paymentMethod": _payment_method(raw, DEFAULT_PAYMENT_METHOD),
            "payNow": raw.get("payNow") is not False,  # chỉ false thật sự mới là giữ ghế
        }


class PayBookingRequest(_Schema):
    username: str = Field(description="Bỏ qua khi bật JWT_REQUIRED: lấy từ token")
    payment_method: str = Field(description="Nhận cả tên cũ `method`")

    @model_validator(mode="before")
    @classmethod
    def _check(cls, raw: dict) -> dict:
        method = _payment_method(raw, "")
        if not method:
            raise ValueError("paymentMethod là bắt buộc")
        return {"username": _owner(raw), "paymentMethod": method}


class CancelBookingRequest(_Schema):
    username: str = Field(description="Bỏ qua khi bật JWT_REQUIRED: lấy từ token")

    @model_validator(mode="before")
    @classmethod
    def _check(cls, raw: dict) -> dict:
        return {"username": _owner(raw)}


class BookingResponse(_Schema):
    id: int
    movie_id: int
    showtime_id: int
    username: str
    seats: list[str]
    total_price: int
    status: str
    created_at: str
    expires_at: str | None

    @classmethod
    def from_entity(cls, booking: Booking) -> "BookingResponse":
        return cls(
            id=booking.id,
            movie_id=booking.movie_id,
            showtime_id=booking.showtime_id,
            username=booking.username,
            seats=booking.seats,
            total_price=booking.total_price,
            status=booking.status,
            created_at=booking.created_at,
            expires_at=booking.expires_at,
        )


class PaymentResponse(_Schema):
    status: str
    method: str
    transaction_id: str | None

    @classmethod
    def from_entity(cls, payment: PaymentOutcome) -> "PaymentResponse":
        return cls(status=payment.status, method=payment.method, transaction_id=payment.transaction_id)


class BookingResultResponse(BookingResponse):
    payment: PaymentResponse | None
    notification: str

    @classmethod
    def from_result(cls, result: BookingResult) -> "BookingResultResponse":
        return cls(
            **BookingResponse.from_entity(result.booking).model_dump(),
            payment=PaymentResponse.from_entity(result.payment) if result.payment else None,
            notification=result.notification,
        )
