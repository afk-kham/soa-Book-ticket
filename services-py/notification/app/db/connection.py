"""Kết nối SQLite của RIÊNG service này (database-per-service).

File DB chỉ được tạo khi có code gọi get_connection(); import/khởi động app thì KHÔNG tạo.
Cấu hình theo D-03: WAL + busy_timeout=5000, row_factory=Row, chạy một worker Uvicorn.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.core import config


@contextmanager
def get_connection():
    """Mở kết nối; commit nếu khối with thành công, rollback nếu có lỗi; luôn đóng."""
    path = Path(config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
