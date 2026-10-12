#!/usr/bin/env bash
# Tạo 5 CSDL MySQL (schema + seed). Chạy từ thư mục gốc:  bash scripts/init-db.sh
# Dùng:  DB_USER=root DB_PASSWORD=matkhau bash scripts/init-db.sh
set -e
cd "$(dirname "$0")/.."
U="${DB_USER:-root}"; H="${DB_HOST:-127.0.0.1}"; P="${DB_PORT:-3306}"
ARGS=(-h "$H" -P "$P" -u "$U" --default-character-set=utf8mb4)
[ -n "$DB_PASSWORD" ] && ARGS+=(-p"$DB_PASSWORD")
for s in movie showtime user booking notification; do
  echo ">> ${s}_db"
  mysql "${ARGS[@]}" < "database/$s/schema.sql"
  mysql "${ARGS[@]}" < "database/$s/seed.sql"
done
echo "OK: đã nạp 5 CSDL MySQL."
if command -v mongosh >/dev/null 2>&1; then
  echo ">> payment_db (MongoDB)"; mongosh --quiet "${MONGO_URI:-mongodb://127.0.0.1:27017}" database/payment/seed.js
else
  echo "LƯU Ý: chưa có mongosh — nạp dữ liệu Payment bằng: mongosh database/payment/seed.js"
fi
