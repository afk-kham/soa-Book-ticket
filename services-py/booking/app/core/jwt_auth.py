"""Verify JWT HS256 theo kế hoạch v2.1 §5. Chỉ dùng khi bật JWT_REQUIRED (chờ D-18)."""
import time

import jwt

from app.core import config
from app.core.errors import BookingError

MIN_SECRET_BYTES = 32
LEEWAY_SECONDS = 60
REQUIRED_CLAIMS = ["sub", "userId", "role", "iat", "exp"]
PAY_TOKEN_TTL_SECONDS = 900


def make_pay_token(booking_id: int, username: str) -> str | None:
    """Tạo token ngắn hạn phạm vi 1 đơn đặt vé cho luồng quét QR trên điện thoại (không cần login)."""
    if len(config.JWT_SECRET.encode("utf-8")) < MIN_SECRET_BYTES:
        return None
    now = int(time.time())
    payload = {
        "scope": "sandbox_pay",
        "bookingId": booking_id,
        "sub": username,
        "iat": now,
        "exp": now + PAY_TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def verify_pay_token(authorization: str | None, booking_id: int) -> dict | None:
    """Xác minh token quét QR; hợp lệ & khớp booking_id -> trả claims tối thiểu, ngược lại None."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    if len(config.JWT_SECRET.encode("utf-8")) < MIN_SECRET_BYTES:
        return None
    try:
        claims = jwt.decode(
            token.strip(),
            config.JWT_SECRET,
            algorithms=["HS256"],
            leeway=LEEWAY_SECONDS,
            options={"require": ["scope", "bookingId", "sub", "iat", "exp"]},
        )
    except jwt.InvalidTokenError:
        return None
    if claims.get("scope") != "sandbox_pay" or claims.get("bookingId") != booking_id:
        return None
    return {"sub": str(claims["sub"]), "role": "USER"}


def verify_bearer(authorization: str | None) -> dict:
    """Trả claims của token trong header Authorization; thiếu hoặc sai token -> UNAUTHORIZED."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise BookingError("UNAUTHORIZED", "Thiếu token xác thực")
    if len(config.JWT_SECRET.encode("utf-8")) < MIN_SECRET_BYTES:
        raise BookingError("UNAUTHORIZED", "Token xác thực không hợp lệ")
    try:
        return jwt.decode(
            token.strip(),
            config.JWT_SECRET,
            algorithms=["HS256"],
            leeway=LEEWAY_SECONDS,
            options={"require": REQUIRED_CLAIMS},
        )
    except jwt.InvalidTokenError as exc:
        raise BookingError("UNAUTHORIZED", "Token xác thực không hợp lệ") from exc
