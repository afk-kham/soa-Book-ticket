"""Khởi tạo schema/seed bằng lệnh tường minh.

Ví dụ: python -m app.db.init_db
Lệnh mặc định vừa tạo schema vừa seed; dùng --no-seed để chỉ tạo schema.
Không chạy khi import hoặc khởi động app.
"""
import argparse
import sqlite3
from pathlib import Path

from app.core import config


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    method TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PAID', 'FAILED')),
    paid_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_transactions_booking_id
ON transactions(booking_id);
"""

SEED_SQL = """
INSERT OR IGNORE INTO transactions
(id, booking_id, amount, method, status, paid_at)
VALUES
(1, 1, 180000, 'MOMO', 'PAID', '2026-10-01T10:01:00Z'),
(2, 2, 85000, 'VNPAY', 'FAILED', '2026-10-01T11:01:00Z');
"""


def init_db(seed: bool = True) -> int:
    path = Path(config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    seeded_count = 0
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA_SQL)
        if seed:
            before_changes = conn.total_changes
            conn.executescript(SEED_SQL)
            seeded_count = conn.total_changes - before_changes

    print(f"Seeded {seeded_count} new row(s) into {path}")
    return seeded_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Chỉ tạo schema, không seed dữ liệu",
    )
    args = parser.parse_args()
    init_db(seed=not args.no_seed)
