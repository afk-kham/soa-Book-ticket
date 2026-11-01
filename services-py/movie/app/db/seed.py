"""Script khởi tạo CSDL và nạp dữ liệu mẫu cho Movie Service.

Chạy:
  python -m app.db.seed
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.db import init_schema, run_seed

if __name__ == "__main__":
    init_schema()
    added = run_seed()
    print(f"✓ Đã khởi tạo schema và nạp {added} phim mới vào CSDL.")
