# API_CONTRACT (bảng đối chiếu) — hợp đồng API 6 service

> **Nguồn sự thật hiện hành vẫn là [`API_CONTRACT.md`](../API_CONTRACT.md) ở thư mục gốc repo.**
> File này là **bảng chi tiết đã đối chiếu với source code thực tế** (nhánh `main` @ `326602e`), để 6 thành viên viết lại bằng Python mà **không đổi hành vi**.
> Chỉ ghi những gì đọc được trong code hoặc contract gốc. Không bịa endpoint/field. Khác biệt được ghi ở cột *Trạng thái* và mục 9, **không tự sửa**.
> Muốn đổi hợp đồng: PR sửa `API_CONTRACT.md` gốc, ≥ 2 người duyệt (gồm chủ service bị ảnh hưởng), cập nhật `CHANGELOG.md`.

**Chú giải trạng thái**
- ✅ **Đã xác minh từ source** (code cũ + contract gốc khớp).
- ⚠️ **Lệch / cần xác nhận** (code ≠ contract hoặc contract không nói rõ).
- 🟡 **Đề xuất, chưa có trong source** (chỉ là hạ tầng khung, cần nhóm duyệt).
- Mọi endpoint nghiệp vụ ở Python: **⬜ chưa triển khai** (khung chỉ có `/health`).

## 1. Quy ước chung (từ contract gốc §1, đã đối chiếu code)

| Mục | Quy định | Ghi chú Python |
|---|---|---|
| Định dạng | JSON UTF-8 `application/json; charset=utf-8` | `ensure_ascii` không phải vấn đề với FastAPI (UTF-8) |
| Tên trường | **camelCase** (`movieId`, `createdAt`); cột DB snake_case | Pydantic `alias_generator=to_camel`, `populate_by_name=True` |
| Thời gian | Movie/Showtime/Booking: `"YYYY-MM-DD HH:MM:SS"`; Payment/Notification: ISO-8601 UTC `…Z` | Không dùng `datetime.isoformat()` mặc định cho nhóm đầu |
| Tiền | Số nguyên VND | Không dùng `float` |
| CORS | `Access-Control-Allow-Origin: *`, headers `Content-Type, Authorization`; `OPTIONS` → **204** | ⚠️ Khung dùng `CORSMiddleware` (preflight trả **200**) — D-07 |
| Envelope OK | `{"status":"success","data":…}`; danh sách rỗng = `[]`, không phải 404 | |
| Envelope lỗi | `{"status":"error","code":"…","message":"<tiếng Việt>"}`; không lộ stack/SQL | ⚠️ FastAPI mặc định trả `{"detail":…}`/422 — D-07 |
| Xác thực | **Chưa có kiểm tra token** ở baseline: `username` lấy từ body; token đăng nhập là chuỗi demo `demo-token-<username>` | Cuối kỳ (kế hoạch v2.1 §5): JWT HS256 + `ADMIN` + `X-Internal-Key` — xem README từng service §10 và D-18 |
| Biến môi trường | Gốc: `PORT, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD` (Payment: `MONGO_URI`, `MONGO_DB`) | ⚠️ SQLite: `DB_PATH` — D-05 |

Mã HTTP chuẩn: 200, 201, 204 (OPTIONS), 400 `VALIDATION_ERROR`, 401 `UNAUTHORIZED`, 403 `FORBIDDEN`, 404 `NOT_FOUND` (+ `USER_/MOVIE_/SHOWTIME_NOT_FOUND`), 405 `METHOD_NOT_ALLOWED`, 409 (`SEAT_TAKEN`, `CONFLICT`, `ALREADY_PAID`, `BOOKING_CANCELLED`, `PAID_NOT_CANCELLABLE`), 413 `PAYLOAD_TOO_LARGE`, 500 `INTERNAL_ERROR`, 502/503 `*_SERVICE_ERROR` / `*_SERVICE_UNAVAILABLE`.

## 2. Movie Service — `:5001` — TV1 — phụ thuộc: không

Đối tượng phim (`data`): `{id:int, title:str, genre:str|null, duration:int|null (phút), poster:str|null, createdAt:"YYYY-MM-DD HH:MM:SS"}`.

| Method + Path | Mục đích | Request | Response `data` | HTTP | Lỗi | Trạng thái |
|---|---|---|---|---|---|---|
| `GET /api/movies` | Danh sách phim, sắp theo `id` tăng | — | `[Phim]` | 200 | 500 `INTERNAL_ERROR` | ✅ |
| `GET /api/movies/{id}` | Chi tiết (`id` là số) | — | `Phim` | 200 | 404 `NOT_FOUND` | ✅ |
| `POST /api/movies` | Thêm phim | `{title (bắt buộc, không rỗng), genre?, duration? (số nguyên > 0), poster?}` | `Phim` vừa tạo | 201 | 400 `VALIDATION_ERROR` (body rỗng/JSON sai/không phải object/title rỗng/duration sai) | ✅ |
| `PUT /api/movies/{id}` | Sửa phim | Các trường của POST; **code: chỉ cập nhật trường được gửi** | `Phim` sau sửa | 200 | 400; 404 `NOT_FOUND` | ⚠️ contract ghi "đủ 4 trường" (D-08) |
| `DELETE /api/movies/{id}` | Xóa phim | — | `{id, deleted:true}` | 200 | 404 `NOT_FOUND` | ✅ |
| `GET /health` | Kiểm tra sống | — | `{service:"movie-service", port:5001}` | 200 | — | 🟡 (D-06) — **chưa có ở code cũ** |
| Đường dẫn khác | — | — | — | 404 `NOT_FOUND` "Endpoint không tồn tại"; method sai trên path hợp lệ → 405 `METHOD_NOT_ALLOWED`; `OPTIONS` → 204 | | ✅ |

## 3. Showtime Service — `:5002` — TV2 — phụ thuộc: **Movie** (HTTP, timeout 3s)

Suất chiếu: `{id:int, movieId:int, cinema:str, room:str, time:"YYYY-MM-DD HH:MM:SS", price:int (VND)}`.

| Method + Path | Mục đích | Request | Response `data` | HTTP | Lỗi | Trạng thái |
|---|---|---|---|---|---|---|
| `GET /api/showtimes` | Danh sách, sắp theo `time, id`. Lọc `?movieId=` (nhận cả `movie_id`), `?upcoming=1\|true` (chỉ suất `time` > bây giờ). **Mỗi lần gọi** tự xếp lịch cho các ngày trong `AUTO_SCHEDULE_DAYS` (mặc định 7) chưa có suất nào | — | `[Suất]` | 200 | 400 (`movieId` không phải số nguyên dương) | ✅ |
| `GET /api/showtimes/{id}` | Chi tiết | — | `Suất` | 200 | 404 `NOT_FOUND` | ✅ |
| `POST /api/showtimes` | Thêm | `{movieId (nhận cả movie_id), cinema ≤150, room ≤50, time ("YYYY-MM-DD HH:MM[:SS]", chấp nhận `T`), price (số nguyên ≥ 0)}` — **cả 5 trường bắt buộc** | `Suất` | 201 | 400 `VALIDATION_ERROR`; 400 `MOVIE_NOT_FOUND`; 503 `MOVIE_SERVICE_UNAVAILABLE` | ✅ |
| `PUT /api/showtimes/{id}` | Sửa một phần (chỉ trường gửi lên, ít nhất 1) | như POST nhưng tùy chọn | `Suất` | 200 | 404 (kiểm tra trước); 400; 400 `MOVIE_NOT_FOUND`; 503 | ✅ |
| `DELETE /api/showtimes/{id}` | Xóa | — | `{id, deleted:true}` | 200 | 404 `NOT_FOUND` | ✅ |
| `GET /health` | Kiểm tra sống | — | `{service:"showtime-service", port:5002}` | 200 | — | ✅ |
| Khác | — | — | — | 404 / 405 (kèm header `Allow`) / `OPTIONS` 204 | | ✅ |

Ghi chú: `VALIDATE_MOVIE=false` tắt việc gọi Movie. Xếp lịch: 3 rạp × 6 khung giờ cố định, phòng `P1..P8`, giá 75.000 (−10.000 trước 12h, +10.000 từ 17h, +15.000 T7/CN); chỉ sinh cho **ngày chưa có suất nào**; lấy danh sách phim qua `GET {Movie}/api/movies`, Movie lỗi thì dùng `movie_id` đã có.

## 4. User/Auth Service — `:5003` — TV3 — phụ thuộc: không

User công khai: `{id:int, username:str, email:str|null, role:"USER"|"ADMIN"}`. `passwordHash` **không bao giờ** xuất hiện.

| Method + Path | Mục đích | Request | Response `data` | HTTP | Lỗi | Trạng thái |
|---|---|---|---|---|---|---|
| `POST /api/register` | Đăng ký (role luôn `USER`, bỏ qua `role` từ client) | `{username (3–50, `[A-Za-z0-9_.]`), password (6–72), email? (≤100, hợp lệ)}` | `{id, username, email, role}` | 201 | 400 `VALIDATION_ERROR`; 409 `CONFLICT` (trùng username) | ✅ |
| `POST /api/login` | Đăng nhập (BCrypt) | `{username, password}` | `{id, username, role, token}` (`token = "demo-token-<username>"`) | 200 | 400 (thiếu trường); 401 `UNAUTHORIZED` (cùng thông báo cho sai user/sai mật khẩu) | ✅ |
| `GET /api/users` | Danh sách; `?username=x` → mảng 0/1 phần tử (Booking dùng) | — | `[User]` | 200 | — | ✅ |
| `GET /api/users/{id}` | Chi tiết | — | `User` | 200 | 400 (`id` không phải số); 404 `NOT_FOUND` | ✅ |
| `GET /health` | Kiểm tra sống | — | `{service:"user-service", port:5003}` | 200 | — | 🟡 (D-06) |
| Khác | — | — | — | 404 / 405 (`Allow`) / `OPTIONS` 204 | | ✅ |

Mật khẩu: BCrypt tiền tố `$2a$` (cost 10). Không có `PUT/DELETE user` trong contract — **không thêm** khi chưa được duyệt.

## 5. Booking Service — `:5004` — TV4 — phụ thuộc: **User, Movie, Showtime, Payment, Notification**

Đơn đặt vé (`Booking`): `{id, movieId, showtimeId, username, seats:[str], totalPrice:int, status:"PENDING"|"PAID"|"CANCELLED", createdAt, expiresAt:str|null}`; `expiresAt` = `createdAt` + `HOLD_MINUTES` chỉ với đơn `PENDING`, còn lại `null`.
Kết quả thao tác (`Result`) = `Booking` + `payment:{status, method, transactionId}|null` + `notification:"SENT"|"FAILED"|"SKIPPED"`.

| Method + Path | Mục đích | Request | Response `data` | HTTP | Lỗi | Trạng thái |
|---|---|---|---|---|---|---|
| `POST /api/booking` | Đặt vé (điều phối). `payNow:false` → chỉ giữ ghế | `{username, movieId, showtimeId, seats:["A5","A6"] (1–10, `^[A-Z]\d{1,2}$`, không trùng), paymentMethod? (mặc định `MOMO`; nhận cả `method`), payNow? }` | `Result` | 201 (kể cả đơn `CANCELLED` do thanh toán `FAILED`) | 400 `VALIDATION_ERROR`/`SHOWTIME_CLOSED`; 404 `USER_/MOVIE_/SHOWTIME_NOT_FOUND`; 409 `SEAT_TAKEN`; 502 `*_SERVICE_ERROR`; 503 `*_SERVICE_UNAVAILABLE` | ✅ |
| `POST /api/booking/{id}/pay` | Thanh toán đơn đang giữ ghế; thất bại/Payment sập → **đơn vẫn PENDING** | `{username, paymentMethod (bắt buộc; nhận cả method)}` | `Result` | 200 | 400; 403 `FORBIDDEN`; 404 `NOT_FOUND`; 409 `ALREADY_PAID` / `BOOKING_CANCELLED`; 502/503 | ✅ |
| `POST /api/booking/{id}/cancel` | Hủy đơn `PENDING` (nhả ghế); đơn đã `CANCELLED` trả lại nguyên trạng | `{username}` | `Result` (`notification:"SKIPPED"`) | 200 | 400; 403; 404; 409 `PAID_NOT_CANCELLABLE` | ✅ |
| `GET /api/booking` | Danh sách; lọc `?username=&status=&showtimeId=` | — | `[Booking]` | 200 | 400 (`status` ∉ 3 giá trị, `showtimeId` không hợp lệ) | ✅ |
| `GET /api/booking/{id}` | Chi tiết | — | `Booking` | 200 | 404 `NOT_FOUND` | ✅ |
| `GET /api/booking/seats?showtimeId=` | Ghế đang giữ (PENDING/PAID) của suất | — | `{showtimeId, seats:[str]}` (sắp tăng) | 200 | 400 | ✅ |
| `GET /api/booking/availability?showtimeIds=1,2,3` | Số ghế đã giữ của nhiều suất (1–500 id) | — | `[{showtimeId, taken}]` | 200 | 400 | ✅ |
| `GET /health` | Kiểm tra sống, **có ping DB** | — | `{service:"booking-service", port:5004}` | 200 | 500 nếu DB lỗi | ✅ |
| Khác | — | — | — | 404 / 405 / `OPTIONS` 204; body > 64 KiB → 413 | | ✅ |

Quy tắc nghiệp vụ cần giữ nguyên: giá **luôn lấy từ Showtime** (`price × số ghế`), không tin client; suất không thuộc phim → 400; suất đã bắt đầu → 400 `SHOWTIME_CLOSED`; ghế bị coi là đã giữ khi đơn `PENDING`/`PAID`; đơn `PENDING` quá `HOLD_MINUTES` tự `CANCELLED` (quét trước mỗi lần đọc/ghi liên quan); chống đặt trùng ghế bằng khóa trong tiến trình; khi Payment không phản hồi thì hỏi lại `GET /api/payment?bookingId=` (timeout 2s) trước khi hủy; Notification lỗi **không** làm hỏng đơn `PAID`.

## 6. Payment Service — `:5005` — TV5 — phụ thuộc: không

Giao dịch: `{id:str, bookingId:int, amount:number, method:str, status:"PAID"|"FAILED", paidAt:"…Z" (ISO-8601 UTC)}`. **`id` là chuỗi** (hiện là ObjectId) — xem D-04.

| Method + Path | Mục đích | Request | Response `data` | HTTP | Lỗi | Trạng thái |
|---|---|---|---|---|---|---|
| `POST /api/payment` | Ghi nhận giao dịch (mô phỏng): `PAID` nếu `amount > 0` và `method ∈ {BANK_TRANSFER, MOMO, VNPAY, CASH}`, ngược lại `FAILED` (**vẫn lưu**, vẫn 201) | `{bookingId (số nguyên > 0), amount (số), method (chuỗi, không phân biệt hoa thường)}` | `Giao dịch` | 201 | 400 `VALIDATION_ERROR`; 409 `ALREADY_PAID` (đơn đã có giao dịch `PAID`); 413 | ✅ |
| `GET /api/payment` | Danh sách, mới nhất trước (`paidAt` giảm); lọc `?bookingId=` | — | `[Giao dịch]` | 200 | 400 (`bookingId` sai) | ✅ |
| `GET /health` | Kiểm tra sống | — | `{service:"payment-service", port:5005}` | 200 | — | ✅ |
| Khác | — | — | — | 404 / 405 (`Allow: GET, POST, OPTIONS` cho `/api/payment`) / `OPTIONS` 204 | | ✅ |

Không có `PUT/DELETE` trong contract — **không thêm** khi chưa được duyệt.

## 7. Notification Service — `:5006` — TV6 — phụ thuộc: không

Nhật ký (`Log`): `{id:int, bookingId:int, username:str, channel:"EMAIL"|"SMS", message:str (≤255), sentAt:"…Z"}`.
Kết quả gửi (`Notify`): `{notificationId, bookingId, username, channel, deliveryStatus:"SIMULATED", message, sentAt}`.

| Method + Path | Mục đích | Request | Response `data` | HTTP | Lỗi | Trạng thái |
|---|---|---|---|---|---|---|
| `POST /api/notify` | Gửi giả lập + ghi log | `{username (1–50), bookingId (1…2147483647), channel (`EMAIL`\|`SMS`)}` — **trường lạ bị từ chối** | `Notify` | 200 | 400; 413 (body > 16 KiB); 500 | ⚠️ contract không nêu mã (code: 200) (D-13) |
| `GET /api/notify/logs` | Danh sách, mới nhất trước; lọc `?bookingId=&username=&channel=` | — | `[Log]` | 200 | 400 | ✅ |
| `POST /api/notify/logs` | Tạo bản ghi log | `{username, bookingId, channel, message?}` (không có `message` thì tự sinh) | `Log` | 201 | 400 | ✅ |
| `GET /api/notify/logs/{id}` | Chi tiết | — | `Log` | 200 | 400 (id không phải số dương); 404 | ✅ |
| `PUT\|PATCH /api/notify/logs/{id}` | Cập nhật (mọi trường tùy chọn) | `{username?, bookingId?, channel?, message?}` | `Log` | 200 | 400; 404 | ✅ |
| `DELETE /api/notify/logs/{id}` | Xóa bản ghi | — | (đối tượng xác nhận xóa) | 200 | 404 | ✅ (xem `services/notification/handler.go` ~dòng 346 để biết đúng hình dạng) |
| `GET /health` | Kiểm tra sống | — | `{service:"notification-service", port:5006}` | 200 | — | 🟡 (D-06) — chưa có ở code cũ |

Không được bỏ/xóa tính năng quản lý log (Admin dùng). Khi test không chạy `DELETE` trên dữ liệu thật.

## 8. Luồng liên service (đã xác minh từ code Booking/Showtime)

Chi tiết sơ đồ ở [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §4. Tóm tắt:

| Luồng | Chuỗi gọi |
|---|---|
| Đặt vé & trả ngay | Client → Booking → User → Movie → Showtime → (khóa + lưu `PENDING`) → Payment → cập nhật `PAID`/`CANCELLED` → Notification (chỉ khi `PAID`) → trả 201 |
| Giữ ghế rồi trả sau | `POST /api/booking {payNow:false}` → `PENDING` + `expiresAt` → `POST /api/booking/{id}/pay` → Payment → `PAID` + Notification |
| Hủy | `POST /api/booking/{id}/cancel` → `CANCELLED` (không gọi service nào) |
| Tạo/sửa suất chiếu | Admin → Showtime → Movie (`GET /api/movies/{id}`) |
| Xếp lịch tự động | `GET /api/showtimes` → Showtime → Movie (`GET /api/movies`) |

Payment và Notification **không bao giờ** gọi ngược Booking.

## 9. Khác biệt / việc cần thống nhất (không tự đổi hợp đồng)

| # | Khác biệt | Xử lý đề xuất | Quyết định |
|---|---|---|---|
| 1 | Movie `PUT`: contract "đủ 4 trường" vs code cập nhật một phần | Giữ hành vi code (không phá Admin) rồi sửa chữ trong contract | D-08 |
| 2 | `/health` thiếu ở Movie, User, Notification | Thêm `/health` cho đủ 6 | D-06 |
| 3 | Payment `id` chuỗi vs SQLite số nguyên; Booking `GetString()` | Giữ `id` kiểu chuỗi trong API (TEXT), hoặc đổi Booking — chọn một | D-04 |
| 4 | Mã 200 của `POST /api/notify` không có trong contract | Ghi vào contract | D-13 |
| 5 | `DB_*`/`MONGO_*` → `DB_PATH` | Sửa contract §1 | D-05 |
| 6 | Preflight 200 (Starlette) vs 204; lỗi 422/`detail` vs envelope | Middleware + exception handler dùng chung | D-07 |
| 7 | Mã `NOT_FOUND` chung vs `*_NOT_FOUND` riêng của Booking | Giữ nguyên như hiện tại | — |
