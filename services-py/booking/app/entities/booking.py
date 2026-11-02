"""Dữ liệu nội bộ của đơn đặt vé (snake_case). Khác Schema (dữ liệu ra/vào API)."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core import config
from app.core.clock import TIME_FORMAT, format_time

PENDING = "PENDING"
PAID = "PAID"
CANCELLED = "CANCELLED"
BOOKING_STATUSES = (PENDING, PAID, CANCELLED)
MAX_ID = 2_147_483_647  # id và tham chiếu là INT 32 bit như schema cũ

NOTIFICATION_SENT = "SENT"
NOTIFICATION_FAILED = "FAILED"
NOTIFICATION_SKIPPED = "SKIPPED"

PAYMENT_PAID = "PAID"
PAYMENT_FAILED = "FAILED"


@dataclass(frozen=True)
class Booking:
    id: int
    movie_id: int
    showtime_id: int
    username: str
    seats: list[str]
    total_price: int
    status: str
    created_at: str

    @property
    def expires_at(self) -> str | None:
        """Hạn giữ ghế của đơn PENDING (= created_at + HOLD_MINUTES); đơn khác trả None."""
        if self.status != PENDING:
            return None
        try:
            created = datetime.strptime(self.created_at, TIME_FORMAT)
        except ValueError:
            return None
        return format_time(created + timedelta(minutes=config.HOLD_MINUTES))


@dataclass(frozen=True)
class PaymentOutcome:
    status: str
    method: str
    transaction_id: str | None


@dataclass(frozen=True)
class BookingResult:
    """Kết quả một thao tác đặt/trả/hủy: đơn + thanh toán + trạng thái thông báo."""

    booking: Booking
    payment: PaymentOutcome | None
    notification: str
