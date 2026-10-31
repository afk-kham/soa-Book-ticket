"""Kết nối SQLite của Movie Service.

- Đọc đường dẫn từ config.DB_PATH mỗi lần kết nối (hỗ trợ test DB tạm thời).
- Tự động tạo thư mục chứa nếu chưa tồn tại.
- Kích hoạt PRAGMA WAL, busy_timeout=5000ms và row_factory = sqlite3.Row.
- Tự động commit khi kết thúc khối with an toàn, rollback khi gặp ngoại lệ.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core import config

BUSY_TIMEOUT_MS = 5000


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    db_path = Path(config.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
