"""DB của Booking Service: kết nối SQLite + khởi tạo schema (idempotent) + seed (chạy tường minh).

- ``init_schema()`` : ``CREATE ... IF NOT EXISTS``; KHÔNG DROP, KHÔNG nạp dữ liệu.
- ``run_seed()``    : nạp 3 đơn mẫu bằng ``INSERT OR IGNORE``; dữ liệu đang có giữ nguyên.

Cả hai chỉ chạy khi được gọi tường minh: ``python -m app.db.init_db [--seed]``.
"""
from pathlib import Path

from app.core import config
from app.db.connection import get_connection

_DIR = Path(__file__).parent
SCHEMA_SQL = _DIR / "schema.sql"
SEED_SQL = _DIR / "seed.sql"

_BOOKING_MIGRATION_COLUMNS = (
    ("movie_title", "TEXT"),
    ("movie_genre", "TEXT"),
    ("unit_price", "INTEGER"),
    ("cinema", "TEXT"),
    ("room", "TEXT"),
    ("show_time", "TEXT"),
)


def migrate_schema(conn) -> None:
    """Bổ sung cột snapshot còn thiếu trên DB bookings cũ (idempotent)."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(bookings)").fetchall()}
    if not existing:
        return
    for column_name, column_type in _BOOKING_MIGRATION_COLUMNS:
        if column_name not in existing:
            conn.execute(f"ALTER TABLE bookings ADD COLUMN {column_name} {column_type}")


def migrate_if_exists() -> None:
    """Bổ sung cột còn thiếu nếu file DB và bảng bookings đã tồn tại (không tạo DB mới)."""
    if not Path(config.DB_PATH).is_file():
        return
    with get_connection() as conn:
        has_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bookings'"
        ).fetchone()
        if has_table:
            migrate_schema(conn)


def init_schema() -> None:
    script = SCHEMA_SQL.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(script)
        migrate_schema(conn)


def run_seed() -> int:
    """Nạp đơn mẫu (không ghi đè). Trả về số dòng thực sự được thêm."""
    script = SEED_SQL.read_text(encoding="utf-8")
    with get_connection() as conn:
        before = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
        conn.executescript(script)
        after = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    return after - before
