#!/usr/bin/env bash
# Tạo/nạp lại DB SQLite cho các service Python (schema + dữ liệu mẫu). Idempotent: INSERT OR IGNORE, KHÔNG xóa dữ liệu có sẵn.
# Chạy từ thư mục gốc:  bash scripts/init-db.sh   (start-all.sh tự tạo DB lần đầu; chỉ cần file này khi muốn nạp lại dữ liệu mẫu)
set -e
cd "$(dirname "$0")/.."
for s in movie showtime user booking payment notification; do
  echo ">> $s"
  bash scripts/run-service.sh "$s" --init-only
done
echo "OK: đã tạo/nạp DB SQLite (services-py/<tên>/data/<tên>.db)."
echo "Showtime tạo bảng tự động khi dùng; lịch chiếu 7 ngày tới do Showtime tự sinh."
