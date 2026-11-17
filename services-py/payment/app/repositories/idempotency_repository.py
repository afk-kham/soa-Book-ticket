"""Kho khóa idempotency của POST /api/payment (bảng idempotency_keys, tạo lười)."""
from dataclasses import dataclass

from app.db.connection import get_connection

_CREATE = """
CREATE TABLE IF NOT EXISTS idempotency_keys (
    idem_key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    response_body TEXT NOT NULL,
    created_at INTEGER NOT NULL
)
"""


@dataclass(frozen=True)
class StoredResponse:
    request_hash: str
    status_code: int
    body: str


def get(key: str) -> StoredResponse | None:
    with get_connection() as conn:
        conn.execute(_CREATE)
        row = conn.execute(
            "SELECT request_hash, status_code, response_body FROM idempotency_keys WHERE idem_key = ?", (key,)
        ).fetchone()
        return None if row is None else StoredResponse(row["request_hash"], row["status_code"], row["response_body"])


def save(key: str, request_hash: str, status_code: int, body: str, now: int) -> None:
    """INSERT OR IGNORE: hai yêu cầu cùng khóa chạy sát nhau thì bản ghi đầu tiên được giữ."""
    with get_connection() as conn:
        conn.execute(_CREATE)
        conn.execute(
            "INSERT OR IGNORE INTO idempotency_keys (idem_key, request_hash, status_code, response_body, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (key, request_hash, status_code, body, now),
        )
        conn.commit()
