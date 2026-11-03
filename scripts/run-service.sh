#!/usr/bin/env bash
# Dùng bởi start-all.sh / init-db.sh:  run-service.sh <tên> [--init-only | --force-init]
#   <tên>: movie | showtime | user | booking | payment | notification   (thư mục services-py/<tên>)
# Việc làm: tạo .venv (nếu chưa có) -> cài requirements.txt -> nạp .env -> tạo/nạp DB SQLite lần đầu -> chạy uvicorn.
#   (không tham số)  tạo DB nếu file DB chưa có, rồi chạy service (chạy ở foreground)
#   --init-only      chỉ tạo/nạp DB (idempotent) rồi thoát
#   --force-init     nạp lại dữ liệu mẫu (INSERT OR IGNORE, không ghi đè) rồi chạy service
# Dời cổng (tuỳ chọn): SOA_PORT_OFFSET=10000 -> 15001..15006 (Admin/Client gọi cứng 5001..5006 nên chỉ dùng khi test API).
set -euo pipefail
NAME=${1:-}; MODE=${2:-}
[ -n "$NAME" ] || { echo "Cách dùng: run-service.sh <tên> [--init-only|--force-init]" >&2; exit 2; }
OFF=${SOA_PORT_OFFSET:-0}
P_MOVIE=$((5001+OFF)); P_SHOWTIME=$((5002+OFF)); P_USER=$((5003+OFF))
P_BOOKING=$((5004+OFF)); P_PAYMENT=$((5005+OFF)); P_NOTIFICATION=$((5006+OFF))

case "$NAME" in   # cổng + lệnh tạo/nạp DB (Showtime tự tạo bảng khi dùng nên không cần)
  movie)        PORT=$P_MOVIE;        INIT=(-m app.db.seed) ;;
  showtime)     PORT=$P_SHOWTIME;     INIT=() ;;
  user)         PORT=$P_USER;         INIT=(-m app.db.seed) ;;
  booking)      PORT=$P_BOOKING;      INIT=(-m app.db.init_db --seed) ;;
  payment)      PORT=$P_PAYMENT;      INIT=(-m app.db.init_db) ;;
  notification) PORT=$P_NOTIFICATION; INIT=(-m app.db.init_db --seed) ;;
  *) echo "[LỖI] Tên service không hợp lệ: $NAME" >&2; exit 2 ;;
esac

cd "$(dirname "$0")/../services-py/$NAME"
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; elif [ -x .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe; else
  echo "[$NAME] Tạo môi trường ảo .venv ..."
  PYBIN=$(command -v python3 || command -v python) || { echo "[LỖI] Chưa có python3 (cần 3.12)" >&2; exit 1; }
  "$PYBIN" -m venv .venv
  if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=.venv/Scripts/python.exe; fi
fi
echo "[$NAME] Kiểm tra thư viện ..."
"$PY" -m pip install -q --disable-pip-version-check -r requirements.txt

if [ -f .env ]; then set -a; . ./.env; set +a; fi   # .env của riêng service (KHÔNG commit)

export HOST=0.0.0.0 PORT PYTHONUTF8=1
export MOVIE_SERVICE_URL=http://127.0.0.1:$P_MOVIE SHOWTIME_SERVICE_URL=http://127.0.0.1:$P_SHOWTIME
export USER_SERVICE_URL=http://127.0.0.1:$P_USER PAYMENT_SERVICE_URL=http://127.0.0.1:$P_PAYMENT
export NOTIFICATION_SERVICE_URL=http://127.0.0.1:$P_NOTIFICATION
export DB_PATH=${DB_PATH:-./data/$NAME.db}   # tương đối so với services-py/<tên> (đang đứng ở đó)

if [ ${#INIT[@]} -gt 0 ]; then
  if [ "$MODE" = "--init-only" ] || [ "$MODE" = "--force-init" ] || [ ! -f "$DB_PATH" ]; then
    echo "[$NAME] Tạo/nạp DB: $DB_PATH"
    "$PY" "${INIT[@]}"
  fi
elif [ "$MODE" = "--init-only" ]; then
  echo "[$NAME] Không cần nạp DB (bảng tự tạo khi dùng)"
fi
[ "$MODE" = "--init-only" ] && exit 0

echo "[$NAME] Chạy tại http://localhost:$PORT  (Swagger: /docs)"
exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
