"""Controller VNPAY Sandbox: tạo URL thanh toán và nhận kết quả chuyển hướng về."""
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.controllers.payment_controller import _error
from app.core import config
from app.schemas import VnpayCreateRequest
from app.services import ServiceError, vnpay


def create_vnpay_url(payload: VnpayCreateRequest, request: Request) -> JSONResponse:
    try:
        ip = request.client.host if request.client else ""
        url, ref = vnpay.build_payment_url(payload.bookingId, payload.amount, ip)
        return JSONResponse(status_code=201, content={"status": "success", "data": {"paymentUrl": url, "txnRef": ref}})
    except ServiceError as exc:
        return _error(exc.status_code, exc.code, exc.message)
    except Exception:
        return _error(500, "INTERNAL_ERROR", "Lỗi máy chủ nội bộ")


def vnpay_return(request: Request):
    """VNPAY chuyển trình duyệt về đây; ghi giao dịch rồi đưa người dùng về Client (#/vnpay-return/<id>/ok|fail)."""
    base = config.CLIENT_URL.rstrip("/")
    try:
        booking_id, ok = vnpay.handle_return(dict(request.query_params))
    except Exception:
        booking_id, ok = None, False
    if booking_id is None:
        return RedirectResponse(f"{base}/#/my", status_code=302)
    return RedirectResponse(f"{base}/#/vnpay-return/{quote(str(booking_id))}/{'ok' if ok else 'fail'}", status_code=302)
