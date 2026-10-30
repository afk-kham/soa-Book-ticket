"""Open the service-owned SQLite database without import/startup side effects."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.core.config import DB_PATH


@contextmanager
def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
