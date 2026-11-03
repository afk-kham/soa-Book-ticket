"""Tích hợp VNPAY Sandbox (v2.1.0): dựng URL thanh toán có chữ ký và kiểm tra kết quả trả về.

Chỉ tính toán/ghi nhận; không biết HTTP. Giao dịch thành công được ghi qua create_payment như mọi giao dịch khác.
"""
import hashlib
import hmac
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

from app.core import config
from app.services.payment_service import ServiceError, create_payment

VN_TZ = timezone(timedelta(hours=7))
_IPV4 = re.compile(r"\d{1,3}(\.\d{1,3}){3}")


def _query(params: dict) -> str:
    return "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted(params.items()))


def _sign(params: dict) -> str:
    return hmac.new(config.VNPAY_HASH_SECRET.encode(), _query(params).encode(), hashlib.sha512).hexdigest()


def configured() -> bool:
    return bool(config.VNPAY_TMN_CODE and config.VNPAY_HASH_SECRET)


def build_payment_url(booking_id: int, amount: int, client_ip: str) -> tuple[str, str]:
    """Trả (paymentUrl, txnRef). txnRef duy nhất mỗi lần thử: <bookingId>_<epoch>."""
    if not configured():
        raise ServiceError(503, "VNPAY_NOT_CONFIGURED", "Chưa cấu hình VNPAY_TMN_CODE / VNPAY_HASH_SECRET")
    if amount <= 0:
        raise ServiceError(400, "VALIDATION_ERROR", "amount phải lớn hơn 0")
    now = datetime.now(VN_TZ)
    txn_ref = f"{booking_id}_{int(time.time())}"
    params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": config.VNPAY_TMN_CODE,
        "vnp_Amount": amount * 100,  # VNPAY tính theo đơn vị nhỏ nhất (x100)
        "vnp_CreateDate": now.strftime("%Y%m%d%H%M%S"),
        "vnp_ExpireDate": (now + timedelta(minutes=15)).strftime("%Y%m%d%H%M%S"),
        "vnp_CurrCode": "VND",
        "vnp_IpAddr": client_ip if _IPV4.fullmatch(client_ip or "") else "127.0.0.1",
        "vnp_Locale": "vn",
        "vnp_OrderInfo": f"Thanh toan ve xem phim don {booking_id}",
        "vnp_OrderType": "other",
        "vnp_ReturnUrl": config.VNPAY_RETURN_URL,
        "vnp_TxnRef": txn_ref,
    }
    return f"{config.VNPAY_URL}?{_query(params)}&vnp_SecureHash={_sign(params)}", txn_ref


def verify_signature(params: dict) -> bool:
    given = params.get("vnp_SecureHash", "")
    signed = {k: v for k, v in params.items() if k.startswith("vnp_") and k not in ("vnp_SecureHash", "vnp_SecureHashType")}
    if not given or not configured():
        return False
    return hmac.compare_digest(_sign(signed).lower(), given.lower())


def handle_return(params: dict) -> tuple[int | None, bool]:
    """Xử lý tham số VNPAY trả về. Trả (bookingId, thành_công); chỉ ghi giao dịch khi chữ ký hợp lệ và mã 00."""
    ref = str(params.get("vnp_TxnRef", ""))
    booking_id = int(ref.split("_")[0]) if re.fullmatch(r"[0-9]+_[0-9]+", ref) else None
    if booking_id is None or not verify_signature(params):
        return None, False
    if params.get("vnp_ResponseCode") != "00" or params.get("vnp_TransactionStatus", "00") != "00":
        return booking_id, False
    try:
        amount = int(params.get("vnp_Amount", "0")) // 100
    except ValueError:
        return booking_id, False
    try:
        create_payment(booking_id, amount, "VNPAY")
    except ServiceError as exc:
        if exc.code != "ALREADY_PAID":  # tải lại trang kết quả: giao dịch đã ghi, vẫn coi là thành công
            raise
    return booking_id, True
