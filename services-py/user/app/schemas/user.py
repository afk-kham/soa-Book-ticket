"""Schema Pydantic cho request/response (camelCase theo API_CONTRACT §4).

Thông báo lỗi bằng tiếng Việt, giữ đúng như code Java cũ. Lỗi validation được
``app/core/http.py`` chuyển thành HTTP 400 ``VALIDATION_ERROR`` (D-07).
Trường lạ (ví dụ ``role``) bị BỎ QUA - không bao giờ được dùng.
"""
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.entities import User

USERNAME_RE = re.compile(r"[A-Za-z0-9_.]{3,50}")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")  # cùng biểu thức với code cũ
PASSWORD_MIN = 6
PASSWORD_MAX = 72  # BCrypt chỉ dùng tối đa 72 BYTE; thư viện bcrypt 5.x báo lỗi nếu vượt
EMAIL_MAX = 100

MSG_USERNAME = "username phải dài 3–50 ký tự, chỉ gồm chữ, số, dấu _ hoặc ."
MSG_PASSWORD = "password phải dài từ 6 đến 72 ký tự"
MSG_EMAIL = "email không hợp lệ"
MSG_LOGIN_MISSING = "Thiếu username hoặc password"
MSG_ROLE = "role phải là USER hoặc ADMIN"
ROLES = ("USER", "ADMIN")


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


# ---------------------------------------------------------------- request
class RegisterRequest(_CamelModel):
    username: str = Field(default="", validate_default=True)
    password: str = Field(default="", validate_default=True)
    email: str | None = None

    @field_validator("username", mode="before")
    @classmethod
    def _check_username(cls, v: Any) -> str:
        if not isinstance(v, str) or not USERNAME_RE.fullmatch(v.strip()):
            raise ValueError(MSG_USERNAME)
        return v.strip()

    @field_validator("password", mode="before")
    @classmethod
    def _check_password(cls, v: Any) -> str:
        if not isinstance(v, str) or not (PASSWORD_MIN <= len(v) <= PASSWORD_MAX):
            raise ValueError(MSG_PASSWORD)
        if len(v.encode("utf-8")) > PASSWORD_MAX:
            raise ValueError(MSG_PASSWORD + " (tối đa 72 byte)")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def _check_email(cls, v: Any) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError(MSG_EMAIL)
        if v.strip() == "":
            return None
        if len(v) > EMAIL_MAX or not EMAIL_RE.fullmatch(v):
            raise ValueError(MSG_EMAIL)
        return v


class CreateUserRequest(RegisterRequest):
    """Admin tạo người dùng: như đăng ký nhưng được chọn ``role`` (mặc định USER)."""

    role: str = "USER"

    @field_validator("role", mode="before")
    @classmethod
    def _check_role(cls, v: Any) -> str:
        if v is None:
            return "USER"
        if not isinstance(v, str) or v.strip().upper() not in ROLES:
            raise ValueError(MSG_ROLE)
        return v.strip().upper()


class UpdateUserRequest(_CamelModel):
    """Sửa một phần: trường nào gửi lên mới đổi. ``email`` rỗng/null -> xóa email."""

    username: str | None = None
    password: str | None = None
    email: str | None = None
    role: str | None = None

    @field_validator("username", mode="before")
    @classmethod
    def _check_username(cls, v: Any) -> str | None:
        return None if v is None else RegisterRequest._check_username(v)

    @field_validator("password", mode="before")
    @classmethod
    def _check_password(cls, v: Any) -> str | None:
        return None if v is None else RegisterRequest._check_password(v)

    @field_validator("email", mode="before")
    @classmethod
    def _check_email(cls, v: Any) -> str | None:
        return RegisterRequest._check_email(v)

    @field_validator("role", mode="before")
    @classmethod
    def _check_role(cls, v: Any) -> str | None:
        return None if v is None else CreateUserRequest._check_role(v)

    def changes(self) -> dict:
        """Các trường được gửi lên (username/password/role null coi như không đổi; email null = xóa email)."""
        sent = self.model_dump(exclude_unset=True)
        return {k: v for k, v in sent.items() if v is not None or k == "email"}


class LoginRequest(_CamelModel):
    username: str = Field(default="", validate_default=True)
    password: str = Field(default="", validate_default=True)

    @field_validator("username", mode="before")
    @classmethod
    def _check_username(cls, v: Any) -> str:
        if not isinstance(v, str) or v.strip() == "":
            raise ValueError(MSG_LOGIN_MISSING)
        return v.strip()

    @field_validator("password", mode="before")
    @classmethod
    def _check_password(cls, v: Any) -> str:
        if not isinstance(v, str) or v == "":
            raise ValueError(MSG_LOGIN_MISSING)
        return v


# --------------------------------------------------------------- response
class UserResponse(_CamelModel):
    """User công khai: ``{id, username, email, role}`` - KHÔNG có mật khẩu/hash."""

    id: int
    username: str
    email: str | None
    role: str

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(id=user.id, username=user.username, email=user.email, role=user.role)


class LoginResponse(_CamelModel):
    id: int
    username: str
    role: str
    token: str
