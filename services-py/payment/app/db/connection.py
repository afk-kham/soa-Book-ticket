"""Kết nối SQLite. Không tạo bảng hoặc nạp dữ liệu."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.core import config


@contextmanager
def get_connection():
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
