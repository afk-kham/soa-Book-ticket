"""OTP xác nhận thanh toán: sinh mã 6 số, lưu băm có muối, kiểm tra hết hạn/số lần sai, dùng một lần."""
import hashlib
import hmac
import secrets
import time

from app.core import config
from app.repositories import otp_repository as repo
from app.services.payment_service import ServiceError


def _digest(salt: str, code: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()


def issue_otp(booking_id: int) -> tuple[str, int]:
    """Sinh OTP mới cho đơn (mã cũ bị thay). Trả (mã, số giây hiệu lực)."""
    now = int(time.time())
    code = f"{secrets.randbelow(10**6):06d}"
    salt = secrets.token_hex(8)
    wait = repo.replace(
        booking_id, salt, _digest(salt, code), now + config.OTP_TTL_SECONDS, now, config.OTP_RESEND_SECONDS
    )
    if wait is not None:
        raise ServiceError(429, "OTP_TOO_SOON", f"Vui lòng chờ {wait} giây rồi yêu cầu gửi lại mã OTP")
    return code, config.OTP_TTL_SECONDS


def verify_and_consume(booking_id: int, otp: str | None) -> None:
    """Chỉ gọi khi OTP bắt buộc hoặc client có gửi `otp`. Đúng thì mã bị xóa (dùng một lần)."""
    if not otp or not otp.strip():
        raise ServiceError(400, "OTP_REQUIRED", "Cần nhập mã OTP để xác nhận thanh toán")
    code = otp.strip()
    result = repo.attempt(
        booking_id,
        int(time.time()),
        config.OTP_MAX_ATTEMPTS,
        lambda ch: hmac.compare_digest(ch.code_hash, _digest(ch.salt, code)),
    )
    if result == "OK":
        return
    if result == "NONE":
        raise ServiceError(400, "OTP_INVALID", "Chưa có mã OTP cho đơn này, hãy yêu cầu gửi mã")
    if result == "EXPIRED":
        raise ServiceError(400, "OTP_EXPIRED", "Mã OTP đã hết hạn, hãy yêu cầu gửi lại mã")
    if result == "LOCKED":
        raise ServiceError(429, "OTP_LOCKED", "Nhập sai quá số lần cho phép, hãy yêu cầu gửi lại mã OTP")
    raise ServiceError(400, "OTP_INVALID", "Mã OTP không đúng")
