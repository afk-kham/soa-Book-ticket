"""DB của Booking Service: kết nối SQLite + khởi tạo schema (idempotent) + seed (chạy tường minh).

- ``init_schema()`` : ``CREATE ... IF NOT EXISTS``; KHÔNG DROP, KHÔNG nạp dữ liệu.
- ``run_seed()``    : nạp 3 đơn mẫu bằng ``INSERT OR IGNORE``; dữ liệu đang có giữ nguyên.

Cả hai chỉ chạy khi được gọi tường minh: ``python -m app.db.init_db [--seed]``.
"""
from pathlib import Path

from app.db.connection import get_connection

_DIR = Path(__file__).parent
SCHEMA_SQL = _DIR / "schema.sql"
SEED_SQL = _DIR / "seed.sql"


def init_schema() -> None:
    script = SCHEMA_SQL.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(script)


def run_seed() -> int:
    """Nạp đơn mẫu (không ghi đè). Trả về số dòng thực sự được thêm."""
    script = SEED_SQL.read_text(encoding="utf-8")
    with get_connection() as conn:
        before = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
        conn.executescript(script)
        after = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    return after - before
