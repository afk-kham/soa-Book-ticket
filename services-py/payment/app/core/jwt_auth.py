"""Verify JWT HS256 cho Payment Service. Không bắt buộc endpoint ở giữa kỳ."""
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core import config


class JwtAuthError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def verify_jwt(token: str) -> dict:
    secret = config.JWT_SECRET
    if len(secret.encode("utf-8")) < 32:
        raise JwtAuthError(401, "UNAUTHORIZED", "Token xác thực không hợp lệ")
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            leeway=60,
            options={"require": ["sub", "userId", "role", "iat", "exp"]},
        )
    except (ExpiredSignatureError, InvalidTokenError):
        raise JwtAuthError(401, "UNAUTHORIZED", "Token xác thực không hợp lệ")


def verify_authorization_header(authorization: str | None, required_role: str | None = None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise JwtAuthError(401, "UNAUTHORIZED", "Thiếu token xác thực")
    token = authorization[7:].strip()
    if not token:
        raise JwtAuthError(401, "UNAUTHORIZED", "Thiếu token xác thực")
    claims = verify_jwt(token)
    if required_role and claims.get("role") != required_role:
        raise JwtAuthError(403, "FORBIDDEN", "Không đủ quyền truy cập")
    return claims
