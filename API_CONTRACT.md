# API_CONTRACT — Hợp đồng API chung của 6 service

> **Đây là nguồn sự thật duy nhất.** Mọi service, trang Admin và Client phải theo file này.
> Muốn đổi hợp đồng: tạo Pull Request sửa chính file này, được cả nhóm đồng ý rồi mới sửa code.

## 1. Quy ước chung

| Mục | Quy định |
|---|---|
| Định dạng | JSON UTF-8, `Content-Type: application/json; charset=utf-8` |
| Tên trường JSON | **camelCase** (`movieId`, `createdAt`). Cột DB vẫn là snake_case — service tự chuyển. |
| Thời gian | Chuỗi `"YYYY-MM-DD HH:MM:SS"` (Movie, Showtime, Booking). Payment/Notification trả ISO-8601 UTC (`2026-10-01T10:01:00Z`). Client hiển thị bằng cách cắt chuỗi. |
| Tiền | Số nguyên VND (`90000`), không dùng số thực. |
| CORS | Mọi response: `Access-Control-Allow-Origin: *`, `Allow-Headers: Content-Type, Authorization`. `OPTIONS` → **204**. |
| Cổng | Movie 5001 · Showtime 5002 · User 5003 · Booking 5004 · Payment 5005 · Notification 5006 · Client 8080 · Admin 8081 |
| Biến môi trường | `PORT`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (Payment: `MONGO_URI`, `MONGO_DB`). Không hard-code. |

### Envelope thành công
```json
{ "status": "success", "data": { } }
```
`data` là object (một đối tượng) hoặc mảng (danh sách). Danh sách rỗng là `"data": []`, **không** phải lỗi 404.

### Envelope lỗi
```json
{ "status": "error", "code": "SEAT_TAKEN", "message": "Ghế đã có người đặt: A1" }
```
`message` đọc được bằng tiếng Việt; `code` để chương trình xử lý. **Không** đưa stack trace / lỗi SQL vào `message`.

### Mã HTTP
| Mã | Khi nào |
|---|---|
| 200 | Đọc/sửa/xóa thành công |
| 201 | Tạo mới thành công (kể cả Payment `FAILED` và Booking `CANCELLED`: giao dịch/đơn đã được ghi nhận) |
| 204 | Chỉ cho `OPTIONS` |
| 400 | Dữ liệu sai (`VALIDATION_ERROR`) hoặc tham chiếu sai (`MOVIE_NOT_FOUND` khi tạo suất chiếu) |
| 401 | Sai tên đăng nhập/mật khẩu (`UNAUTHORIZED`) |
| 404 | Không có tài nguyên (`NOT_FOUND`, `USER_NOT_FOUND`, `MOVIE_NOT_FOUND`, `SHOWTIME_NOT_FOUND`) |
| 405 | Sai phương thức (`METHOD_NOT_ALLOWED`) |
| 409 | Xung đột: `SEAT_TAKEN`, `CONFLICT` (trùng username), `ALREADY_PAID` |
| 413 | Body quá lớn |
| 500 | Lỗi nội bộ (`INTERNAL_ERROR`) |
| 502 / 503 | Booking gọi service khác lỗi / không với tới được (`*_SERVICE_ERROR`, `*_SERVICE_UNAVAILABLE`) |

## 2. Movie Service — `:5001`
| Method | Đường dẫn | Mô tả |
|---|---|---|
| GET | `/api/movies` | Danh sách phim |
| GET | `/api/movies/{id}` | Chi tiết |
| POST | `/api/movies` | Thêm `{title, genre, duration, poster}` → 201 |
| PUT | `/api/movies/{id}` | Sửa (đủ 4 trường) |
| DELETE | `/api/movies/{id}` | Xóa |

Phim: `{ "id": 1, "title": "Avengers: Endgame", "genre": "Hành động", "duration": 181, "poster": "poster1.jpg", "createdAt": "2026-10-01 09:00:00" }`

## 3. Showtime Service — `:5002`
| Method | Đường dẫn | Mô tả |
|---|---|---|
| GET | `/api/showtimes` | Danh sách; lọc `?movieId=1`, `?upcoming=1` (chỉ suất chưa bắt đầu). Mỗi lần gọi, service tự xếp lịch cho các ngày trong `AUTO_SCHEDULE_DAYS` (mặc định 7) **chưa có suất nào** — không đụng suất đã có. |
| GET | `/api/showtimes/{id}` | Chi tiết |
| POST | `/api/showtimes` | Thêm `{movieId, cinema, room, time, price}` → 201. Showtime gọi `GET {Movie}/api/movies/{movieId}` để kiểm tra phim có thật. |
| PUT | `/api/showtimes/{id}` | Sửa một phần (chỉ gửi trường cần đổi) |
| DELETE | `/api/showtimes/{id}` | Xóa |
| GET | `/health` | `{"service":"showtime-service","port":5002}` |

Suất chiếu: `{ "id": 1, "movieId": 1, "cinema": "CGV Vincom", "room": "P1", "time": "2026-10-10 18:00:00", "price": 90000 }`
Tên cũ `movie_id` (query và body) vẫn được nhận để tương thích, nhưng **response luôn là `movieId`**.

## 4. User/Auth Service — `:5003`
| Method | Đường dẫn | Mô tả |
|---|---|---|
| POST | `/api/register` | `{username, password, email?}` → 201 · trùng username → **409** |
| POST | `/api/login` | `{username, password}` → `{id, username, role, token}` · sai → 401 |
| GET | `/api/users` | Danh sách (không có mật khẩu); `?username=x` tìm một người (Booking dùng) |
| GET | `/api/users/{id}` | Chi tiết |

`token` ở giữa kỳ là token demo (`demo-token-<username>`). Cuối kỳ: JWT ký bằng **một** `JWT_SECRET` chung; Booking đọc `sub` từ token thay vì tin `username` trong body.
Mật khẩu băm BCrypt; `passwordHash` **không bao giờ** xuất hiện trong response.

## 5. Booking Service — `:5004` (điều phối)
| Method | Đường dẫn | Mô tả |
|---|---|---|
| POST | `/api/booking` | Đặt vé (xem dưới) → 201 |
| POST | `/api/booking/{id}/pay` | Thanh toán đơn đang giữ ghế `{username, paymentMethod}` → 200. Thất bại / Payment tạm sập: đơn **vẫn PENDING** để thử lại. Đơn đã trả → 409 `ALREADY_PAID`; đã hủy/hết hạn → 409 `BOOKING_CANCELLED`; không phải chủ đơn → 403 `FORBIDDEN`. |
| POST | `/api/booking/{id}/cancel` | Hủy đơn đang giữ ghế `{username}` → 200 (nhả ghế). Đơn đã trả → 409 `PAID_NOT_CANCELLABLE`. |
| GET | `/api/booking` | Danh sách; lọc `?username=&status=&showtimeId=` |
| GET | `/api/booking/{id}` | Chi tiết |
| GET | `/api/booking/seats?showtimeId=1` | Ghế đang bị giữ (PENDING/PAID) — Client vẽ sơ đồ ghế |
| GET | `/api/booking/availability?showtimeIds=1,2,3` | `[{showtimeId, taken}]` — số ghế đã bị giữ của nhiều suất (Client hiện "còn N ghế") |
| GET | `/health` | Kiểm tra sống (có ping DB) |

**Request**
```json
{ "username": "user1", "movieId": 1, "showtimeId": 1, "seats": ["A5", "A6"], "paymentMethod": "MOMO" }
```
Ghế dạng chữ hoa + 1–2 chữ số (`A1`, `B12`), 1–10 ghế, không trùng. `paymentMethod` mặc định `MOMO`.
`"payNow": false` → chỉ **giữ ghế**: trả đơn `PENDING` kèm `expiresAt` (= `createdAt` + `HOLD_MINUTES`, mặc định 10 phút), chưa gọi Payment; người dùng thanh toán qua `/pay`. Quá hạn, Booking tự chuyển đơn sang `CANCELLED` và nhả ghế.
Suất chiếu đã bắt đầu → 400 `SHOWTIME_CLOSED`.
Giá **luôn lấy từ Showtime**; Booking không tin giá do client gửi.

**Response 201**
```json
{ "status": "success", "data": {
  "id": 4, "movieId": 1, "showtimeId": 1, "username": "user1", "seats": ["A5","A6"],
  "totalPrice": 180000, "status": "PAID", "createdAt": "2026-10-06 10:00:00",
  "payment": { "status": "PAID", "method": "MOMO", "transactionId": "665f..." },
  "notification": "SENT" } }
```
`status` ∈ `PENDING | PAID | CANCELLED`. `notification` ∈ `SENT | FAILED | SKIPPED` (SKIPPED khi thanh toán thất bại hoặc chỉ giữ ghế).
Mọi đơn (kể cả `GET`) có thêm `expiresAt`: hạn giữ ghế của đơn `PENDING`, `null` với đơn khác.

## 6. Payment Service — `:5005`
| Method | Đường dẫn | Mô tả |
|---|---|---|
| POST | `/api/payment` | `{bookingId, amount, method}` (`method` ∈ `BANK_TRANSFER`, `MOMO`, `VNPAY`, `CASH`) → 201 `{id, bookingId, amount, method, status, paidAt}`. `status` = `PAID` hoặc `FAILED` (vẫn lưu). Đơn đã `PAID` mà gọi lại → **409 `ALREADY_PAID`**. |
| GET | `/api/payment` | Danh sách; lọc `?bookingId=` |
| GET | `/health` | Kiểm tra sống |

## 7. Notification Service — `:5006`
| Method | Đường dẫn | Mô tả |
|---|---|---|
| POST | `/api/notify` | `{username, bookingId, channel}` → `{notificationId, bookingId, username, channel, deliveryStatus, message, sentAt}`. Gửi giả lập, có ghi log. |
| GET | `/api/notify/logs` | Danh sách nhật ký gửi (mới nhất trước). Hỗ trợ lọc `?bookingId=&username=&channel=` |
| POST | `/api/notify/logs` | `{username, bookingId, channel, message?}` → Tạo bản ghi nhật ký thông báo mới |
| GET | `/api/notify/logs/{id}` | Chi tiết một bản ghi nhật ký thông báo theo ID |
| PUT / PATCH | `/api/notify/logs/{id}` | `{username?, bookingId?, channel?, message?}` → Cập nhật bản ghi nhật ký thông báo |
| DELETE | `/api/notify/logs/{id}` | Xóa một bản ghi nhật ký thông báo theo ID |

## 8. Thay đổi hợp đồng
Sửa file này → PR → ít nhất **2 thành viên** (gồm người sở hữu service bị ảnh hưởng) duyệt → cập nhật `CHANGELOG.md`.
