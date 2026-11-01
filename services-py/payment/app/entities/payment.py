"""Entity dữ liệu nội bộ, ánh xạ cột snake_case của SQLite."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentTransaction:
    id: int
    booking_id: int
    amount: int
    method: str
    status: str
    paid_at: str
