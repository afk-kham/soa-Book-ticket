# ARCHITECTURE — Kiến trúc 3 lớp + Entity/Repository cho từng service Python

Tài liệu này bổ sung (không thay thế) `ARCHITECTURE.md` ở thư mục gốc. Phần nào mâu thuẫn với bản gốc: xem `AUDIT_REPORT.md` M2 và `OPEN_QUESTIONS.md` D-12.

## 1. Vai trò từng lớp trong `app/`

| Thư mục | Lớp | Trách nhiệm | **Không** được làm |
|---|---|---|---|
| `api/router.py` | **Router** | Khai báo route, HTTP method, path, mã trả về; nối tới controller | Chứa logic nghiệp vụ, SQL |
| `controllers/` | **Controller** | Nhận request đã parse (Schema), kiểm tra đầu vào mức cơ bản, gọi Service, dựng response/envelope | Truy cập SQLite, gọi service khác trực tiếp |
| `services/` | **Service** | **Logic nghiệp vụ** (quy tắc, tính giá, gọi service khác qua HTTP, điều phối) | Viết SQL, biết chuyện HTTP (status code) |
| `repositories/` | **Repository** | Truy cập SQLite: mọi câu SQL nằm ở đây, trả về Entity | Chứa quy tắc nghiệp vụ |
| `entities/` | **Entity/Model** | Đối tượng dữ liệu **nội bộ** (ánh xạ bảng; tên cột snake_case) | Dùng làm response API |
| `schemas/` | **Schema** (Pydantic) | Hình dạng **request/response API** (camelCase theo hợp đồng) | Chứa logic truy cập DB |
| `db/` | **DB** | Kết nối SQLite, khởi tạo schema/migration (TODO) | SQL nghiệp vụ |
| `core/` | **Core** | `config.py` (biến môi trường), logging, tiện ích riêng của service | Import từ service khác |
| `tests/` | Test | Test của service (database tạm, **không** dùng dữ liệu thật) | |

Thứ tự phụ thuộc (chỉ gọi xuống, không gọi ngược): `Router → Controller → Service → Repository → db`.
**Entity ≠ Schema:** Entity là dữ liệu nội bộ (ví dụ `movie_id`, `created_at`); Schema là dữ liệu ra/vào API (ví dụ `movieId`, `createdAt`). Chuyển đổi một chiều ở Controller hoặc Service. Không tạo lớp trùng chức năng (ví dụ không thêm `dao/`, `models/` song song với `entities/`).

Thứ tự viết code một endpoint mới: **Schema → Entity → Repository → Service → Controller → Router → test**.

## 2. Mapping dữ liệu: cột SQLite ↔ trường JSON

Cột DB giữ snake_case, JSON camelCase (hợp đồng §1). Ví dụ: `movie_id` ↔ `movieId`, `created_at` ↔ `createdAt`, `total_price` ↔ `totalPrice`, `showtime_id` ↔ `showtimeId`, `booking_id` ↔ `bookingId`, `sent_at` ↔ `sentAt`, `password_hash` ↔ *(không bao giờ trả ra)*.

## 3. Quy tắc SQLite

1. **Một service = một file `.db` = một volume.** Không service nào mở file của service khác; muốn dữ liệu của họ → gọi API.
2. **Không khóa ngoại xuyên service**; tham chiếu `movie_id`, `showtime_id`, `username`, `booking_id` là tham chiếu logic.
3. **Không tạo schema/seed ở thời điểm import hoặc khởi động ngầm.** Khởi tạo schema là bước tường minh (script/migration có số phiên bản), idempotent: `CREATE TABLE IF NOT EXISTS`. **Cấm `DROP`/`DELETE` hàng loạt trong schema/seed** (các file MySQL cũ có `DROP TABLE`, `DROP DATABASE`, `DELETE FROM` — không được chuyển nguyên sang).
4. Truy vấn luôn dùng tham số hóa (`?`), không nối chuỗi.
5. Kiểu dữ liệu: `INTEGER PRIMARY KEY AUTOINCREMENT` thay `AUTO_INCREMENT`; thời gian lưu `TEXT 'YYYY-MM-DD HH:MM:SS'` (đúng định dạng hợp đồng); tiền `INTEGER`; `CHECK` ràng buộc trạng thái giữ nguyên như Booking đang có.
6. Đồng thời: SQLite chỉ **một writer** tại một thời điểm. Cấu hình đề xuất (chờ D-03): `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, một tiến trình Uvicorn / service, giao dịch ngắn. Các chỗ cần khóa nguyên tử: Showtime xếp lịch (D-09), Booking giữ ghế (D-10).
7. Seed dùng chung: **giữ nguyên id và giá trị** các dòng cũ (test tích hợp và tài liệu nhóm dựa vào chúng); thêm dữ liệu mới = dòng mới id lớn hơn. Tài khoản mẫu: `admin/Admin@123`, `user1/User@123`, `user2/User@123` (BCrypt).
8. Migration dữ liệu MySQL/MongoDB → SQLite là **giai đoạn riêng**: sao lưu nguồn trước, đối chiếu số dòng/checksum sau, không ghi đè DB thật, không chạy trên máy production.
9. Sao lưu: xem `README.md` §7.

## 4. Luồng liên service (đã xác minh từ code)

### 4.1 Đặt vé và thanh toán ngay (`POST /api/booking`)

```mermaid
sequenceDiagram
    participant C as Client
    participant B as Booking :5004
    participant U as User :5003
    participant M as Movie :5001
    participant S as Showtime :5002
    participant P as Payment :5005
    participant N as Notification :5006
    C->>B: POST /api/booking {username, movieId, showtimeId, seats}
    B->>U: GET /api/users?username=
    B->>M: GET /api/movies/{movieId}
    B->>S: GET /api/showtimes/{showtimeId}  (price, movieId, time)
    Note over B: kiểm tra suất chưa bắt đầu, ghế trống (khóa), total = price x số ghế
    Note over B: INSERT booking = PENDING
    B->>P: POST /api/payment {bookingId, amount, method}
    P-->>B: 201 {status: PAID | FAILED}
    Note over B: UPDATE booking -> PAID hoặc CANCELLED
    B->>N: POST /api/notify (chỉ khi PAID; timeout 3s)
    B-->>C: 201 {booking, payment, notification}
```

### 4.2 Giữ ghế rồi thanh toán sau / hủy

- `POST /api/booking {payNow:false}` → lưu `PENDING` + `expiresAt`, **không** gọi Payment/Notification (`notification: SKIPPED`).
- `POST /api/booking/{id}/pay` → kiểm tra chủ đơn → Payment → `PAID` + Notification; thất bại/Payment sập → đơn **vẫn `PENDING`** để thử lại.
- `POST /api/booking/{id}/cancel` → `PENDING` → `CANCELLED` (nhả ghế); đơn `PAID` → 409 `PAID_NOT_CANCELLABLE`.
- Đơn `PENDING` quá `HOLD_MINUTES` tự `CANCELLED` (Booking quét trước mỗi lần đọc/ghi liên quan).

### 4.3 Showtime ↔ Movie

- `POST/PUT /api/showtimes` → `GET {Movie}/api/movies/{id}` (timeout 3s; tắt bằng `VALIDATE_MOVIE=false`).
- `GET /api/showtimes` → xếp lịch cho ngày chưa có suất → `GET {Movie}/api/movies` (Movie sập thì dùng `movie_id` đang có).

### 4.4 Bảng xử lý khi đối tác lỗi (từ `INTEGRATION_FLOW.md`, khớp code Booking)

| Tình huống | Booking làm gì | Client nhận |
|---|---|---|
| Body/ghế sai định dạng | Từ chối trước khi gọi ai | 400 `VALIDATION_ERROR` |
| User/Movie/Showtime không tồn tại | Dừng, chưa lưu | 404 `*_NOT_FOUND` |
| Ghế đã giữ | Dừng, chưa lưu | 409 `SEAT_TAKEN` |
| User/Movie/Showtime sập | Dừng, chưa lưu | 503 `*_SERVICE_UNAVAILABLE` |
| Payment trả `FAILED` | Đơn → `CANCELLED`, không gọi Notification | 201, `status: CANCELLED` |
| Payment sập / >5s | Hỏi lại `GET /api/payment?bookingId=`; không có → `CANCELLED` | 503 `PAYMENT_SERVICE_UNAVAILABLE` |
| Notification sập | Đơn vẫn `PAID` | 201, `notification: FAILED` |
| Thanh toán lại đơn đã `PAID` | Payment từ chối | 409 `ALREADY_PAID` |

Giới hạn đã biết (kế thừa): không có giao dịch phân tán (dùng trạng thái + bù trừ kiểu Saga đơn giản); nếu Payment ghi `PAID` nhưng mất cả phản hồi lẫn lần hỏi lại thì cần đối soát thủ công; khóa giữ ghế hiện nằm trong tiến trình (một instance).

## 5. Cấu hình & Docker

- Mỗi service đọc cấu hình từ biến môi trường (`app/core/config.py`); URL service khác **chỉ** nằm ở đó.
- Trong Docker Compose: gọi nhau bằng **tên service + cổng nội bộ** (`http://movie:5001`); trình duyệt gọi bằng **cổng publish** `localhost:5001`.
- Dockerfile: `python:3.12.12-slim-bookworm`, chạy bằng user không phải root, volume `/data`, `HEALTHCHECK` gọi `/health` bằng thư viện chuẩn (không cần `curl`).
- Không có reverse proxy / API Gateway (ngoài phạm vi đã xác nhận).

## 6. Dependency ngoài fastapi/uvicorn (đã pin trong khung)

| Gói | Phiên bản | Service | Lý do |
|---|---|---|---|
| `PyJWT` | 2.15.1 | cả 6 | Verify JWT (cuối kỳ); User còn **cấp** token |
| `httpx` | 0.28.1 | Showtime, Booking | Gọi service khác (có timeout) |
| `bcrypt` | 5.0.0 | User | Hash/kiểm tra mật khẩu, đọc được `$2a$` |

Notification chỉ thêm `PyJWT` vì `GET /api/notify/logs` yêu cầu `ADMIN`; `POST /api/notify` chỉ kiểm tra header `X-Internal-Key`. `sqlite3`, `zoneinfo` có sẵn trong thư viện chuẩn Python 3.12. Gói khác chỉ thêm bằng PR (D-11).
