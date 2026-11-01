"""Quản lý CSDL SQLite cho Movie Service."""
from pathlib import Path

from app.db.connection import get_connection

_DIR = Path(__file__).parent
SCHEMA_SQL = _DIR / "schema.sql"
SEED_SQL = _DIR / "seed.sql"


def init_schema() -> None:
    """Khởi tạo bảng movies nếu chưa có (idempotent, không xóa dữ liệu)."""
    script = SCHEMA_SQL.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(script)


def run_seed() -> int:
    """Nạp 5 bộ phim mẫu (INSERT OR IGNORE). Trả về số lượng dòng mới được thêm."""
    script = SEED_SQL.read_text(encoding="utf-8")
    with get_connection() as conn:
        before = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        conn.executescript(script)
        after = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    return after - before


def init_db(seed: bool = False) -> None:
    """Khởi tạo toàn bộ CSDL và nạp dữ liệu mẫu nếu seed=True."""
    init_schema()
    if seed:
        run_seed()


__all__ = ["get_connection", "init_schema", "run_seed", "init_db"]
