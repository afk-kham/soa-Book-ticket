# MIGRATION_TRACKER — Theo dõi chuyển đổi từng service

Cập nhật bảng này trong PR của mình. **Không tích ✅ nếu chưa có code + test chạy thật.** Hiện trạng ở thời điểm dựng khung: chỉ cột "Khung" có dấu.

Ký hiệu: ⬜ chưa làm · 🟨 đang làm · ✅ xong (kèm test) · ⛔ bị chặn (ghi ID quyết định)

## 1. Tổng quan theo service

| Service | TV | Khung (FastAPI + Docker + health) | Schema SQLite | Seed | Router/Controller/Service/Repo | Test nghiệp vụ | Tương đương với service cũ | Migration dữ liệu | Ghi chú / chặn |
|---|---|---|---|---|---|---|---|---|---|
| Movie | TV1 | ✅ (health, pytest 2/2) | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | D-01, D-06, D-07, D-08 |
| Showtime | TV2 | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | D-01, D-07, D-09, D-11 |
| User | TV3 | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | D-01, D-06, D-07, D-11, D-18 |
| Booking | TV4 | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | D-01, D-04, D-07, D-10, D-11 |
| Payment | TV5 | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | D-01, D-04, D-07 |
| Notification | TV6 | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | D-01, D-06, D-07, D-13 |

## 2. Theo endpoint (điền khi triển khai)

Cột *Cũ* = đã xác minh trong code cũ; *Py* = trạng thái bản Python. Mỗi dòng ✅ phải có test tham chiếu.

| Service | Endpoint | Cũ | Py | Test | Người | PR |
|---|---|---|---|---|---|---|
| Movie | `GET /api/movies` | ✅ | ⬜ | | TV1 | |
| Movie | `GET /api/movies/{id}` | ✅ | ⬜ | | TV1 | |
| Movie | `POST /api/movies` | ✅ | ⬜ | | TV1 | |
| Movie | `PUT /api/movies/{id}` | ✅ | ⬜ | | TV1 | |
| Movie | `DELETE /api/movies/{id}` | ✅ | ⬜ | | TV1 | |
| Movie | `GET /health` | — (mới) | ✅ khung | `tests/test_scaffold.py` | TV1 | |
| Showtime | `GET /api/showtimes` (+ lọc, + xếp lịch) | ✅ | ⬜ | | TV2 | |
| Showtime | `GET /api/showtimes/{id}` | ✅ | ⬜ | | TV2 | |
| Showtime | `POST /api/showtimes` | ✅ | ⬜ | | TV2 | |
| Showtime | `PUT /api/showtimes/{id}` | ✅ | ⬜ | | TV2 | |
| Showtime | `DELETE /api/showtimes/{id}` | ✅ | ⬜ | | TV2 | |
| Showtime | `GET /health` | ✅ | ✅ khung | `tests/test_scaffold.py` | TV2 | |
| User | `POST /api/register` | ✅ | ⬜ | | TV3 | |
| User | `POST /api/login` | ✅ | ⬜ | | TV3 | |
| User | `GET /api/users` (+ `?username=`) | ✅ | ⬜ | | TV3 | |
| User | `GET /api/users/{id}` | ✅ | ⬜ | | TV3 | |
| User | `GET /health` | — (mới) | ✅ khung | `tests/test_scaffold.py` | TV3 | |
| Booking | `POST /api/booking` | ✅ | ⬜ | | TV4 | |
| Booking | `POST /api/booking/{id}/pay` | ✅ | ⬜ | | TV4 | |
| Booking | `POST /api/booking/{id}/cancel` | ✅ | ⬜ | | TV4 | |
| Booking | `GET /api/booking` | ✅ | ⬜ | | TV4 | |
| Booking | `GET /api/booking/{id}` | ✅ | ⬜ | | TV4 | |
| Booking | `GET /api/booking/seats` | ✅ | ⬜ | | TV4 | |
| Booking | `GET /api/booking/availability` | ✅ | ⬜ | | TV4 | |
| Booking | `GET /health` (ping DB) | ✅ | 🟨 khung chưa ping DB | `tests/test_scaffold.py` | TV4 | |
| Payment | `POST /api/payment` | ✅ | ⬜ | | TV5 | |
| Payment | `GET /api/payment` (+ `?bookingId=`) | ✅ | ⬜ | | TV5 | |
| Payment | `GET /health` | ✅ | ✅ khung | `tests/test_scaffold.py` | TV5 | |
| Notification | `POST /api/notify` | ✅ | ⬜ | | TV6 | |
| Notification | `GET /api/notify/logs` | ✅ | ⬜ | | TV6 | |
| Notification | `POST /api/notify/logs` | ✅ | ⬜ | | TV6 | |
| Notification | `GET /api/notify/logs/{id}` | ✅ | ⬜ | | TV6 | |
| Notification | `PUT\|PATCH /api/notify/logs/{id}` | ✅ | ⬜ | | TV6 | |
| Notification | `DELETE /api/notify/logs/{id}` | ✅ | ⬜ | | TV6 | |
| Notification | `GET /health` | — (mới) | ✅ khung | `tests/test_scaffold.py` | TV6 | |

## 3. Theo dữ liệu (migration dữ liệu — giai đoạn riêng)

| Service | Nguồn hiện tại | Đích | Dữ liệu seed cần giữ id | Trạng thái |
|---|---|---|---|---|
| Movie | MySQL `movie_db.movies` | `movie.db` bảng `movies` | `database/movie/seed.sql` | ⬜ chờ D-01, D-16 |
| Showtime | MySQL `showtime_db.showtimes` | `showtime.db` | `database/showtime/seed.sql` | ⬜ |
| User | MySQL `user_db.users` (BCrypt) | `user.db` | `database/user/seed.sql` (admin, user1, user2) | ⬜ |
| Booking | MySQL `booking_db.bookings` | `booking.db` | `database/booking/seed.sql` (3 đơn: PAID, CANCELLED, PENDING) | ⬜ |
| Payment | MongoDB `payment_db.transactions` | `payment.db` | `database/payment/seed.js` (2 giao dịch) | ⬜ chờ D-04 |
| Notification | MySQL `notification_db.notification_logs` | `notification.db` | `database/notification/seed.sql` | ⬜ |

Quy trình mỗi dòng: (1) sao lưu nguồn (ngoài repo) → (2) tạo schema SQLite idempotent → (3) nạp seed/dữ liệu bằng script tường minh → (4) đối chiếu số dòng + vài bản ghi mẫu → (5) chạy `tests/integration/run_tests.py` với service Python → (6) ghi kết quả vào PR. **Không bao giờ** chạy `DROP`/`DELETE` bằng file cũ trên dữ liệu thật.

## 4. Tiêu chí "tương đương" của một service (để tích ✅)

- [ ] Mọi endpoint ở §2 trả đúng method/path/envelope/camelCase/mã HTTP/mã lỗi như bảng `API_CONTRACT.md`.
- [ ] `/health` và `OPTIONS → 204` + CORS `*` đúng hợp đồng (sau D-07).
- [ ] Không lộ `passwordHash`, `_id`, lỗi SQL, stack trace.
- [ ] Test của service pass (DB tạm); `tests/integration/run_tests.py` pass với service này chạy cùng các service còn lại.
- [ ] Chạy được bằng Docker Compose; dữ liệu nằm trong volume riêng.
- [ ] README service cập nhật; `MIGRATION_TRACKER.md` cập nhật.
