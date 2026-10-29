"""Kết nối SQLite ở mức khung. KHÔNG tạo bảng, KHÔNG nạp dữ liệu.

File DB chỉ được tạo khi có code gọi get_connection() (lúc import/khởi động thì KHÔNG tạo).
TODO(TV4): sau khi nhóm chốt D-03 (xem docs/OPEN_QUESTIONS.md) hãy bổ sung PRAGMA
(vd journal_mode=WAL, busy_timeout), row_factory và phần khởi tạo schema.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.core.config import DB_PATH


@contextmanager
def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
