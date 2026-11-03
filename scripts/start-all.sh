#!/usr/bin/env bash
# Chạy cả 6 service Python (services-py) + Admin (8081) + Client (8080), mỗi cái là MỘT TIẾN TRÌNH RIÊNG. Dừng: bash scripts/stop-all.sh
# Cần: python3 (3.12). Lần đầu mỗi service tự tạo .venv, cài thư viện và tạo DB SQLite (services-py/<tên>/data/<tên>.db).
cd "$(dirname "$0")/.."
ROOT=$(pwd); mkdir -p .run

start() {  # start <tên> <thư mục chạy> <lệnh...>
  local name=$1 dir=$2; shift 2
  ( cd "$ROOT/$dir" && nohup "$@" > "$ROOT/.run/$name.log" 2>&1 & echo $! > "$ROOT/.run/$name.pid" )
  echo "  $name  (log: .run/$name.log)"
}

echo "Khởi động các service..."
for s in movie showtime user booking payment notification; do
  start "$s" . bash scripts/run-service.sh "$s"
done
start admin  admin  python3 -m http.server 8081
start client client python3 -m http.server 8080
echo
echo "Admin : http://localhost:8081      Client: http://localhost:8080      Swagger mỗi service: http://localhost:500x/docs"
echo "Lần đầu chờ ~1 phút (cài thư viện). Theo dõi: tail -f .run/<tên>.log     Kiểm tra: python3 tests/integration/run_tests.py"
