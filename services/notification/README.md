# Notification Service (TV6) — Go · cổng 5006 · `notification_db`

Gửi thông báo (giả lập) và ghi nhật ký. Go 1.21+, `net/http` + `database/sql` + go-sql-driver/mysql.

```bash
cd services/notification
cp .env.example .env
set -a; . ./.env; set +a          # service Go chỉ đọc biến môi trường (scripts/start-all làm giúp)
go run .                          # http://localhost:5006
go test ./...
```
Biến: `PORT` (hoặc `HTTP_ADDR=host:port`), `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
Tài liệu chi tiết của TV6: `docs/api.md`.
