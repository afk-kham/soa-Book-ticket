"""Kết nối SQLite của User Service.

- Đọc đường dẫn từ ``config.DB_PATH`` MỖI LẦN mở kết nối (để test đổi sang DB tạm được).
- File DB chỉ được tạo khi có code gọi ``get_connection()``; import module KHÔNG tạo file.
- PRAGMA theo đề xuất D-03: WAL + busy_timeout; ``row_factory = sqlite3.Row``.
- Tự ``commit`` khi khối ``with`` kết thúc êm, ``rollback`` khi có lỗi, luôn đóng kết nối.
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
    conn = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000)
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
