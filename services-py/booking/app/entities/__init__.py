"""Entity/Model: đối tượng dữ liệu NỘI BỘ (ánh xạ bảng SQLite). Khác Schema (dữ liệu API)."""
from app.entities.booking import (
    BOOKING_STATUSES,
    CANCELLED,
    MAX_ID,
    NOTIFICATION_FAILED,
    NOTIFICATION_SENT,
    NOTIFICATION_SKIPPED,
    PAID,
    PAYMENT_FAILED,
    PAYMENT_PAID,
    PENDING,
    Booking,
    BookingResult,
    PaymentOutcome,
)

__all__ = [
    "BOOKING_STATUSES",
    "CANCELLED",
    "MAX_ID",
    "NOTIFICATION_FAILED",
    "NOTIFICATION_SENT",
    "NOTIFICATION_SKIPPED",
    "PAID",
    "PAYMENT_FAILED",
    "PAYMENT_PAID",
    "PENDING",
    "Booking",
    "BookingResult",
    "PaymentOutcome",
]
