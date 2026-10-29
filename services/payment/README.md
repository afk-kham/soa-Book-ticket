# Payment Service (TV5) — Node.js · cổng 5005 · `payment_db` (MongoDB)

Ghi nhận giao dịch thanh toán (giả lập). Node.js 18+, module `http` thuần, driver `mongodb`.

```bash
cd services/payment
npm install
cp .env.example .env              # MONGO_URI, MONGO_DB, PORT
node payment_service.js           # http://localhost:5005
npm test                          # 8 test, không cần MongoDB
```
Nạp dữ liệu mẫu: `mongosh database/payment/seed.js`.
Không có MongoDB? Dùng `node tests/integration/tools/payment_in_memory.js` (công cụ test, dữ liệu mất khi tắt).

- `POST /api/payment` → 201 với `status` `PAID`/`FAILED`; đơn đã PAID → 409 `ALREADY_PAID`.
- `GET /api/payment[?bookingId=]`.
