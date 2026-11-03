"""Nạp 6 suất chiếu lịch sử của dữ liệu mẫu dùng chung (database/showtime/seed.sql).

Các đơn mẫu của Booking trỏ vào suất id 1–6; thiếu chúng thì lịch tự sinh chiếm mất id 1–6
và giá/phim của đơn mẫu không khớp. INSERT OR IGNORE: không ghi đè, không xóa dữ liệu đang có.

Chạy:
  python -m app.db.seed
"""
import sys

from app.db.connection import get_connection
from app.repositories import _ensure_schema

# GIỮ NGUYÊN id và giá trị của database/showtime/seed.sql
HISTORY = [
    (1, 1, "CGV Vincom Đồng Khởi", "P1", "2026-10-10 18:00:00", 90000),
    (2, 1, "CGV Vincom Đồng Khởi", "P2", "2026-10-10 21:00:00", 100000),
    (3, 2, "Lotte Cinema Cantavil", "P1", "2026-10-11 19:30:00", 85000),
    (4, 3, "BHD Star Bitexco", "P3", "2026-10-11 20:00:00", 80000),
    (5, 4, "CGV Vincom Đồng Khởi", "P3", "2026-10-12 17:30:00", 90000),
    (6, 5, "Lotte Cinema Cantavil", "P2", "2026-10-12 15:00:00", 75000),
]


def run_seed() -> int:
    """Trả số suất mới được thêm (0 nếu đã có đủ)."""
    with get_connection() as conn:
        _ensure_schema(conn)
        cur = conn.executemany(
            "INSERT OR IGNORE INTO showtimes (id, movie_id, cinema, room, time, price) VALUES (?, ?, ?, ?, ?, ?)",
            HISTORY,
        )
        conn.commit()
        return cur.rowcount


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"Đã nạp {run_seed()} suất chiếu lịch sử vào CSDL.")
