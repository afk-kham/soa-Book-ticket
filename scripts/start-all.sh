#!/usr/bin/env bash
# Chạy cả 6 service + Admin (8081) + Client (8080), mỗi cái là MỘT TIẾN TRÌNH RIÊNG. Dừng: bash scripts/stop-all.sh
# Cần: python3, php, java 17+ & maven, dotnet 8, node 18+, go 1.21+, MySQL, MongoDB.
cd "$(dirname "$0")/.."
ROOT=$(pwd); mkdir -p .run

start() {  # start <tên> <thư mục> <lệnh...>
  local name=$1 dir=$2; shift 2
  ( cd "$ROOT/$dir"
    if [ -f .env ]; then set -a; . ./.env; set +a; fi      # nạp .env của riêng service
    nohup "$@" > "$ROOT/.run/$name.log" 2>&1 &
    echo $! > "$ROOT/.run/$name.pid" )
  echo "  $name  (log: .run/$name.log)"
}

echo "Khởi động các service..."
start movie        services/movie        python3 movie_service.py
start showtime     services/showtime     php -S 0.0.0.0:"${SHOWTIME_PORT:-5002}" router.php
start user         services/user         bash -c 'mvn -q compile dependency:build-classpath -Dmdep.outputFile=target/cp.txt && exec java -cp "target/classes:$(cat target/cp.txt)" userservice.Main'   # exec:java không nạp được driver JDBC
start booking      services/booking      dotnet run
start payment      services/payment      node payment_service.js
start notification services/notification go run .
start admin        admin                 python3 -m http.server 8081
start client       client                python3 -m http.server 8080
echo
echo "Admin : http://localhost:8081      Client: http://localhost:8080"
echo "Kiểm tra: python3 tests/integration/run_tests.py   (đợi ~20 giây cho Java/.NET khởi động lần đầu)"
