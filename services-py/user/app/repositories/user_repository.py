"""Repository: toàn bộ SQL của bảng ``users`` (tham số hóa bằng ``?``). Không có quy tắc nghiệp vụ."""
import sqlite3

from app.db.connection import get_connection
from app.entities import User, UserAccount

_PUBLIC_COLUMNS = "id, username, email, role"  # danh sách công khai: KHÔNG chọn password_hash


class DuplicateUsernameError(Exception):
    """Vi phạm ràng buộc UNIQUE(username) ở mức database."""


def _to_user(row: sqlite3.Row) -> User:
    return User(id=row["id"], username=row["username"], email=row["email"], role=row["role"])


class UserRepository:
    def find_account_by_username(self, username: str) -> UserAccount | None:
        """Lấy cả password_hash - chỉ phục vụ đăng nhập."""
        sql = "SELECT id, username, password_hash, email, role FROM users WHERE username = ?"
        with get_connection() as conn:
            row = conn.execute(sql, (username,)).fetchone()
        if row is None:
            return None
        return UserAccount(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            email=row["email"],
            role=row["role"],
        )

    def find_by_username(self, username: str) -> User | None:
        sql = f"SELECT {_PUBLIC_COLUMNS} FROM users WHERE username = ?"
        with get_connection() as conn:
            row = conn.execute(sql, (username,)).fetchone()
        return _to_user(row) if row else None

    def find_by_id(self, user_id: int) -> User | None:
        sql = f"SELECT {_PUBLIC_COLUMNS} FROM users WHERE id = ?"
        with get_connection() as conn:
            row = conn.execute(sql, (user_id,)).fetchone()
        return _to_user(row) if row else None

    def find_all(self) -> list[User]:
        sql = f"SELECT {_PUBLIC_COLUMNS} FROM users ORDER BY id"
        with get_connection() as conn:
            rows = conn.execute(sql).fetchall()
        return [_to_user(r) for r in rows]

    def insert(self, username: str, password_hash: str, email: str | None) -> User:
        """Thêm người dùng với role ``USER``. Ném ``DuplicateUsernameError`` nếu trùng username."""
        sql = "INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, 'USER')"
        try:
            with get_connection() as conn:
                cur = conn.execute(sql, (username, password_hash, email))
                new_id = cur.lastrowid
        except sqlite3.IntegrityError as exc:
            if "users.username" in str(exc) or "UNIQUE" in str(exc).upper():
                raise DuplicateUsernameError(username) from exc
            raise
        return User(id=new_id, username=username, email=email, role="USER")
