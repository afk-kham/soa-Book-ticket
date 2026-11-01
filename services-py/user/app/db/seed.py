"""Seed tường minh: ``python -m app.db.seed`` (chạy trong thư mục services-py/user).

Không bao giờ chạy tự động. Tạo schema nếu chưa có, rồi ``INSERT OR IGNORE`` 3 tài khoản mẫu
(admin, user1, user2). Dữ liệu đã có (trùng id hoặc username) được giữ nguyên.
"""
from app.core import config
from app.db import init_schema, run_seed


def main() -> None:
    init_schema()
    added = run_seed()
    print(f"[seed] DB: {config.DB_PATH} - đã thêm {added} tài khoản mẫu (bỏ qua các dòng đã có).")


if __name__ == "__main__":
    main()
