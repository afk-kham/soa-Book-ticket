# DATABASE_CONTRACT — Mỗi service một CSDL riêng

**Nguyên tắc vàng:** CSDL thuộc về đúng **một** service. Không service nào được kết nối vào CSDL của service khác,
không dùng khóa ngoại (FOREIGN KEY) giữa các CSDL. Muốn dữ liệu của service khác → **gọi API của họ**.

| Service | CSDL | Công nghệ | Bảng / collection | Người sở hữu |
|---|---|---|---|---|
| Movie | `movie_db` | MySQL | `movies` | TV1 |
| Showtime | `showtime_db` | MySQL | `showtimes` | TV2 |
| User | `user_db` | MySQL | `users` | TV3 |
| Booking | `booking_db` | MySQL | `bookings` | TV4 |
| Payment | `payment_db` | MongoDB | `transactions` | TV5 |
| Notification | `notification_db` | MySQL | `notification_logs` | TV6 |

> Tên CSDL cố định như trên. **Không** dùng tên khác (ví dụ `cinema_db`).

## Tham chiếu logic (không phải khóa ngoại)
- `showtimes.movie_id` → id của phim trong Movie Service. Showtime kiểm tra bằng `GET /api/movies/{id}`.
- `bookings.movie_id`, `bookings.showtime_id`, `bookings.username` → Movie / Showtime / User. Booking kiểm tra bằng API trước khi lưu.
- `transactions.bookingId` và `notification_logs.booking_id` → `bookings.id`. Hai service này chỉ **lưu** mã đơn, không đọc `booking_db`.

## Schema & dữ liệu mẫu
Thư mục `database/<service>/` chứa `schema.sql` (tạo CSDL + bảng) và `seed.sql` (dữ liệu mẫu chung).
- Chạy theo thứ tự: `schema.sql` rồi `seed.sql`. Chạy lại nhiều lần an toàn (seed xóa và nạp lại).
- **Không đổi id và giá trị** các dòng seed có sẵn — bộ test tích hợp và tài liệu của cả nhóm dựa vào chúng.
  Muốn thêm dữ liệu mẫu: thêm dòng **mới** với id lớn hơn.
- Luôn nạp bằng UTF-8: `mysql --default-character-set=utf8mb4 < file.sql` (file seed đã có `SET NAMES utf8mb4`).
- `database/booking/booking_db.sqlserver.sql`: bản SQL Server của kế hoạch ban đầu — **không dùng** với code Booking hiện tại (MySQL).
- Payment (MongoDB): `database/payment/seed.js` → `mongosh database/payment/seed.js`.

## Trạng thái & ràng buộc dùng chung
- Booking: `status ∈ PENDING | PAID | CANCELLED`; `seats` lưu dạng `"A1,A2"`; `total_price` số nguyên VND.
- Payment: `status ∈ PAID | FAILED`.
- Ghế bị coi là đã giữ khi đơn ở `PENDING` hoặc `PAID`; đơn `CANCELLED` nhả ghế.
- Mật khẩu: chỉ lưu băm BCrypt (`password_hash`). Tài khoản mẫu: `admin / Admin@123`, `user1 / User@123`, `user2 / User@123`.

## Tài khoản MySQL
Dev: dùng `root` hoặc tạo user riêng, đặt trong `.env` của **từng service** (không commit). Không dùng chung một file `.env` cho cả nhóm.
