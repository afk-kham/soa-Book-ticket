"""Khởi tạo CSDL (bước tường minh): ``python -m app.db.init_db [--seed]``.

Chạy lại nhiều lần an toàn: chỉ ``CREATE ... IF NOT EXISTS`` và ``INSERT OR IGNORE``.
"""
import argparse

from app.core import config
from app.db import init_schema, run_seed


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo schema SQLite của Booking Service")
    parser.add_argument("--seed", action="store_true", help="nạp thêm 3 đơn mẫu dùng chung của nhóm")
    args = parser.parse_args()

    init_schema()
    print(f"[init_db] Schema sẵn sàng: {config.DB_PATH}")
    if args.seed:
        print(f"[init_db] Đã thêm {run_seed()} đơn mẫu (bỏ qua các dòng đã có).")


if __name__ == "__main__":
    main()
