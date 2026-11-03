"""Verify JWT HS256 theo kế hoạch v2.1 §5. Chỉ dùng khi bật JWT_REQUIRED (chờ D-18)."""
import jwt

from app.core import config
from app.core.errors import BookingError

MIN_SECRET_BYTES = 32
LEEWAY_SECONDS = 60
REQUIRED_CLAIMS = ["sub", "userId", "role", "iat", "exp"]


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
