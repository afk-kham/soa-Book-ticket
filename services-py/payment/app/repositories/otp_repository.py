"""Kho lưu thử thách OTP của từng đơn (bảng otp_challenges). Chỉ lưu băm, không lưu mã gốc."""
import sqlite3
from dataclasses import dataclass
from typing import Callable

from app.db.connection import get_connection

_CREATE = """
CREATE TABLE IF NOT EXISTS otp_challenges (
    booking_id INTEGER PRIMARY KEY,
    salt TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0
)
"""


@dataclass(frozen=True)
class Challenge:
    booking_id: int
    salt: str
    code_hash: str
    expires_at: int
    created_at: int
    attempts: int


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE)  # tạo lười: DB cũ chưa có bảng vẫn chạy được


def _challenge(row) -> Challenge | None:
    if row is None:
        return None
    keys = ("booking_id", "salt", "code_hash", "expires_at", "created_at", "attempts")
    return Challenge(*(row[k] for k in keys))


def get(booking_id: int) -> Challenge | None:
    with get_connection() as conn:
        _ensure(conn)
        return _challenge(conn.execute("SELECT * FROM otp_challenges WHERE booking_id = ?", (booking_id,)).fetchone())


def replace(booking_id: int, salt: str, code_hash: str, expires_at: int, now: int, min_gap: int) -> int | None:
    """Ghi thử thách mới (thay mã cũ). Trả None nếu thành công, hoặc số giây phải chờ nếu gửi lại quá sớm."""
    with get_connection() as conn:
        _ensure(conn)
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT created_at FROM otp_challenges WHERE booking_id = ?", (booking_id,)).fetchone()
            if row is not None and now - row["created_at"] < min_gap:
                conn.rollback()
                return min_gap - (now - row["created_at"])
            conn.execute(
                "INSERT OR REPLACE INTO otp_challenges (booking_id, salt, code_hash, expires_at, created_at, attempts) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                (booking_id, salt, code_hash, expires_at, now),
            )
            conn.commit()
            return None
        except Exception:
            conn.rollback()
            raise


def attempt(booking_id: int, now: int, max_attempts: int, matches: Callable[[Challenge], bool]) -> str:
    """Thử một mã trong MỘT giao dịch ghi (hai yêu cầu song song không dùng chung một lượt thử).

    Trả: NONE | EXPIRED | LOCKED | MISMATCH | OK. OK xóa thử thách (mã dùng một lần); MISMATCH tăng số lần sai.
    """
    with get_connection() as conn:
        _ensure(conn)
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT * FROM otp_challenges WHERE booking_id = ?", (booking_id,)).fetchone()
            ch = _challenge(row)
            if ch is None:
                result = "NONE"
            elif ch.expires_at <= now:
                conn.execute("DELETE FROM otp_challenges WHERE booking_id = ?", (booking_id,))
                result = "EXPIRED"
            elif ch.attempts >= max_attempts:
                result = "LOCKED"
            elif matches(ch):
                conn.execute("DELETE FROM otp_challenges WHERE booking_id = ?", (booking_id,))
                result = "OK"
            else:
                conn.execute("UPDATE otp_challenges SET attempts = attempts + 1 WHERE booking_id = ?", (booking_id,))
                result = "LOCKED" if ch.attempts + 1 >= max_attempts else "MISMATCH"
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
