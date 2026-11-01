"""Entity nội bộ của User Service (ánh xạ bảng ``users``; cột snake_case).

Khác Schema: Entity KHÔNG dùng để trả ra API trực tiếp.
- ``User``        : dữ liệu công khai (không có mật khẩu).
- ``UserAccount`` : thêm ``password_hash`` - CHỈ dùng nội bộ cho đăng nhập, không bao giờ trả ra ngoài.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    username: str
    email: str | None
    role: str


@dataclass(frozen=True, repr=False)
class UserAccount:
    id: int
    username: str
    password_hash: str
    email: str | None
    role: str

    def __repr__(self) -> str:  # không để lộ hash khi log/in debug
        return f"UserAccount(id={self.id}, username={self.username!r}, role={self.role!r})"

    def to_user(self) -> User:
        return User(id=self.id, username=self.username, email=self.email, role=self.role)
