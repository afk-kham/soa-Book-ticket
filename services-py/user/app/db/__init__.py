"""DB của User Service: kết nối SQLite + khởi tạo schema (idempotent) + seed (chạy tường minh).

- ``init_schema()``  : ``CREATE TABLE IF NOT EXISTS``; KHÔNG DROP, KHÔNG nạp dữ liệu.
                       Được gọi khi ứng dụng khởi động (lifespan), KHÔNG gọi lúc import module.
- ``run_seed()``     : nạp 3 tài khoản mẫu bằng ``INSERT OR IGNORE``; chỉ chạy khi được yêu cầu
                       (``python -m app.db.seed``), không bao giờ tự chạy.
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
    """Nạp tài khoản mẫu (không ghi đè). Trả về số dòng thực sự được thêm."""
    script = SEED_SQL.read_text(encoding="utf-8")
    with get_connection() as conn:
        before = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.executescript(script)
        after = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return after - before
