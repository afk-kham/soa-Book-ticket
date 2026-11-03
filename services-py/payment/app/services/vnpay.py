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
LINK_LIFETIME = timedelta(minutes=15)
# Link hết hạn sớm hơn hạn giữ ghế để kịp chuyển về Client và Booking chốt đơn trước khi đơn bị hủy
RETURN_MARGIN = timedelta(minutes=1)


def _query(params: dict) -> str:
    return "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted(params.items()))


def _sign(params: dict) -> str:
    return hmac.new(config.VNPAY_HASH_SECRET.encode(), _query(params).encode(), hashlib.sha512).hexdigest()


def configured() -> bool:
    return bool(config.VNPAY_TMN_CODE and config.VNPAY_HASH_SECRET)


def _parse_time(value: str) -> datetime:
    """expiresAt của Booking: "YYYY-MM-DD HH:MM:SS" theo giờ Việt Nam, hoặc ISO-8601 có múi giờ."""
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        raise ServiceError(400, "VALIDATION_ERROR", "expiresAt không đúng định dạng thời gian") from None
    return parsed.replace(tzinfo=VN_TZ) if parsed.tzinfo is None else parsed


def build_payment_url(booking_id: int, amount: int, client_ip: str, expires_at: str | None = None) -> tuple[str, str]:
    """Trả (paymentUrl, txnRef). txnRef duy nhất mỗi lần thử: <bookingId>_<epoch>.

    Có expires_at (hạn giữ ghế) thì link hết hạn trước đó RETURN_MARGIN, để không thể trả tiền cho đơn đã bị hủy.
    """
    if not configured():
        raise ServiceError(503, "VNPAY_NOT_CONFIGURED", "Chưa cấu hình VNPAY_TMN_CODE / VNPAY_HASH_SECRET")
    if amount <= 0:
        raise ServiceError(400, "VALIDATION_ERROR", "amount phải lớn hơn 0")
    now = datetime.now(VN_TZ)
    expire = now + LINK_LIFETIME
    if expires_at is not None:
        pay_by = _parse_time(expires_at).astimezone(VN_TZ) - RETURN_MARGIN
        if pay_by <= now:
            raise ServiceError(409, "HOLD_EXPIRED",
                               "Đơn sắp hết thời gian giữ ghế nên không thể chuyển sang VNPAY. "
                               "Vui lòng chọn phương thức khác hoặc đặt lại.")
        expire = min(expire, pay_by)
    txn_ref = f"{booking_id}_{int(time.time())}"
    params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": config.VNPAY_TMN_CODE,
        "vnp_Amount": amount * 100,  # VNPAY tính theo đơn vị nhỏ nhất (x100)
        "vnp_CreateDate": now.strftime("%Y%m%d%H%M%S"),
        "vnp_ExpireDate": expire.strftime("%Y%m%d%H%M%S"),
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
