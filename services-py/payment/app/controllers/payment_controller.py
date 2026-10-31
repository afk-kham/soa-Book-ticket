"""Controller dựng HTTP response/envelope cho Payment Service."""
from fastapi import status
from fastapi.responses import JSONResponse

from app.entities import PaymentTransaction
from app.schemas import PaymentCreateRequest
from app.services import ServiceError, create_payment, get_payments


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


def post_payment(payload: PaymentCreateRequest) -> JSONResponse:
    try:
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
