"""Controller dựng HTTP response/envelope cho Payment Service."""
import hashlib
import json
import re
import threading
import time

from fastapi import status
from fastapi.responses import JSONResponse

from app.entities import PaymentTransaction
from app.repositories import idempotency_repository as idem_repo
from app.schemas import PaymentCreateRequest
from app.core import config
from app.services import ServiceError, create_payment, get_payments, otp_service


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"status": "error", "code": code, "message": message},
    )


def _serialize(transaction: PaymentTransaction) -> dict:
    return {
        "id": str(transaction.id),
        "bookingId": transaction.booking_id,
        "amount": transaction.amount,
        "method": transaction.method,
        "status": transaction.status,
        "paidAt": transaction.paid_at,
    }


_KEY_RE = re.compile(r"[A-Za-z0-9._:-]{1,64}")
_idem_lock = threading.Lock()  # một tiến trình duy nhất ghi SQLite: tuần tự hóa các yêu cầu có khóa (chống chạy đôi)


def post_payment(payload: PaymentCreateRequest, idempotency_key: str | None = None) -> JSONResponse:
    """Không có khóa: như cũ. Có `Idempotency-Key`: gửi lại cùng khóa + cùng nội dung -> trả lại ĐÚNG kết quả lần đầu
    (không trừ tiền hai lần, không cần OTP mới); cùng khóa nhưng khác nội dung -> 409 IDEMPOTENCY_KEY_REUSED."""
    if idempotency_key is None:
        return _post_payment(payload)
    if not _KEY_RE.fullmatch(idempotency_key):
        return _error(400, "VALIDATION_ERROR", "Idempotency-Key phải gồm 1-64 ký tự chữ, số, . _ : -")
    fingerprint = hashlib.sha256(
        f"{payload.bookingId}|{payload.amount}|{payload.method.strip().upper()}".encode()).hexdigest()
    with _idem_lock:
        try:
            stored = idem_repo.get(idempotency_key)
            if stored is not None:
                if stored.request_hash != fingerprint:
                    return _error(409, "IDEMPOTENCY_KEY_REUSED", "Idempotency-Key này đã được dùng cho một yêu cầu khác")
                return JSONResponse(status_code=stored.status_code, content=json.loads(stored.body),
                                    headers={"Idempotency-Replayed": "true"})
            response = _post_payment(payload)
            if response.status_code == status.HTTP_201_CREATED:  # chỉ lưu kết quả thành công; lỗi (OTP sai...) được thử lại
                idem_repo.save(idempotency_key, fingerprint, response.status_code, response.body.decode(), int(time.time()))
            return response
        except Exception:
            return _error(500, "INTERNAL_ERROR", "Lỗi máy chủ nội bộ")


def _post_payment(payload: PaymentCreateRequest) -> JSONResponse:
    try:
        if config.OTP_REQUIRED or payload.otp is not None:
            otp_service.verify_and_consume(payload.bookingId, payload.otp)
        transaction = create_payment(payload.bookingId, payload.amount, payload.method)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": "success", "data": _serialize(transaction)},
        )
    except ServiceError as exc:
        return _error(exc.status_code, exc.code, exc.message)
    except Exception:
        return _error(500, "INTERNAL_ERROR", "Lỗi máy chủ nội bộ")


def get_payments_controller(booking_id: int | None = None) -> JSONResponse:
    try:
        transactions = get_payments(booking_id)
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data": [_serialize(transaction) for transaction in transactions],
            },
        )
    except Exception:
        return _error(500, "INTERNAL_ERROR", "Lỗi máy chủ nội bộ")


def post_otp(booking_id: int) -> JSONResponse:
    """Dành cho service nội bộ (Booking): sinh OTP và trả mã để Booking nhờ Notification gửi email."""
    try:
        code, ttl = otp_service.issue_otp(booking_id)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": "success", "data": {"bookingId": booking_id, "otp": code, "ttlSeconds": ttl}},
        )
    except ServiceError as exc:
        return _error(exc.status_code, exc.code, exc.message)
    except Exception:
        return _error(500, "INTERNAL_ERROR", "Lỗi máy chủ nội bộ")
