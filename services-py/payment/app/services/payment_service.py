"""Logic nghiệp vụ Payment. Không biết HTTP và không viết SQL."""
from datetime import datetime, timezone

from app.entities import PaymentTransaction
from app.repositories import create_transaction, list_transactions


ALLOWED_METHODS = {"BANK_TRANSFER", "MOMO", "VNPAY", "CASH"}


class ServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def create_payment(booking_id: int, amount: int, method: str) -> PaymentTransaction:
    normalized_method = method.strip().upper()
    status = "PAID" if amount > 0 and normalized_method in ALLOWED_METHODS else "FAILED"
    transaction = PaymentTransaction(
        id=0,
        booking_id=booking_id,
        amount=amount,
        method=normalized_method,
        status=status,
        paid_at=_utc_now_z(),
    )
    stored, already_paid = create_transaction(transaction)
    if already_paid or stored is None:
        raise ServiceError(409, "ALREADY_PAID", f"Đơn #{booking_id} đã được thanh toán")
    return stored


def get_payments(booking_id: int | None = None) -> list[PaymentTransaction]:
    return list_transactions(booking_id)
