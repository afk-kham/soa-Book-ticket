# CHANGELOG

## Baseline V2 — bổ sung sản phẩm của TV2 và TV4
Chỉ **thêm** tài liệu/ý tưởng của hai thành viên; không đổi code đã tích hợp (Showtime, Booking, Admin, Client giữ nguyên).

### TV2 — Showtime
- `docs/tv2-showtime/`: thêm ERD, Use Case, DFD mức 0/1/2 (`.png` + `.drawio`) và `baocao_showtime.md` (kèm ghi chú: API hiện dùng `movieId`, lỗi có `code`).
- Mã nguồn `services/showtime/`: không đổi — bản của TV2 (`router.php`, `src/*`) trùng với bản đã chuẩn hóa trong baseline.

### TV4 — Booking
- `docs/tv4-booking/`: thêm ERD, Use Case, DFD mức 0/1/2, báo cáo `05_baocao_booking.docx` (+ PDF), ảnh kết quả chạy `anh-ket-qua/`.
- `docs/tong-the/`: thêm `UC_TongThe` và `DFD1_TongThe` (sản phẩm chung do TV4 phụ trách) + README.
- `docs/tv4-booking/source-giua-ky/`: lưu bản Booking giữa kỳ (test đơn vị + test API, docker-compose, SQL Server idempotent, `demo_api.ps1`) để tham khảo — **không** nằm trong `services/` nên không ảnh hưởng build/run.
- `docs/tv4-booking/admin_booking_giua_ky.html`: trang admin giữa kỳ, giữ để tham khảo; trang chính thức vẫn là `admin/pages/booking.html` (khung chung).
- `database/booking/schema.sql`: thêm 2 chỉ mục (`showtime_id,status` và `username`) và 2 ràng buộc CHECK (`status`, `total_price >= 0`) theo thiết kế của TV4. Dữ liệu mẫu và tên cột không đổi.
- `scripts/demo-booking.ps1`: bản cập nhật của `demo_api.ps1` cho API tích hợp (409 `SEAT_TAKEN`, có `code` trong lỗi).

## Baseline V2 (tạo lại repository)
Lý do: các thành viên làm theo ý mình nên API, CSDL và giao diện không đồng nhất. Bản này giữ phần đã tốt của từng người và chuẩn hóa phần còn lại.

### Toàn hệ thống
- Thống nhất cấu trúc `services/ database/ admin/ client/ tests/ docs/` và bộ tài liệu hợp đồng (`API_CONTRACT`, `DATABASE_CONTRACT`, `INTEGRATION_FLOW`, `ARCHITECTURE`, `TEAM_RULES`, `INTEGRATION_CHECKLIST`).
- Một envelope duy nhất `{"status","data"}` / `{"status","code","message"}`; trường JSON camelCase; CORS `*`; `OPTIONS` → 204.
- Seed chung tách thành `schema.sql` + `seed.sql` cho từng CSDL, đặt `SET NAMES utf8mb4`.
- Admin: 7 trang dùng chung một khung (`admin.css`, `common.js`, `config.js`) thay cho 4 giao diện riêng lẻ.
- Client mới (đăng nhập, phim, suất chiếu, sơ đồ ghế, đặt vé, vé của tôi).
- Bộ test tích hợp `tests/integration/run_tests.py` (41 kiểm tra + 4 kịch bản service sập).

### Theo service
| Service | Giữ nguyên | Đã sửa / thêm |
|---|---|---|
| **Movie (TV1)** | Toàn bộ logic CRUD, `ThreadingHTTPServer`, schema, seed, báo cáo, sơ đồ | `created_at` → `createdAt`; lỗi có `code`; không trả chi tiết lỗi DB cho client; body không phải object → 400; đọc `.env`, biến `PORT` |
| **Showtime (TV2)** | Ý tưởng PHP thuần + PDO | **Viết lại**: dùng `showtime_db` (không phải `cinema_db`), có đủ POST/PUT/DELETE, `/api/showtimes`, không hard-code mật khẩu, `OPTIONS` 204, kiểm tra `movieId` qua API Movie, seed chuẩn của nhóm |
| **User (TV3)** | `Config`, `UserDao`, BCrypt, schema, seed, báo cáo, sơ đồ | Envelope chung; CORS `*`; trùng username → 409; thêm `GET /api/users?username=`; **thêm `pom.xml`**; sửa README (biến `DB_PASSWORD`) |
| **Booking (TV4)** | — (chưa có code) | **Viết mới** bằng C# `HttpListener` + ADO.NET: điều phối User/Movie/Showtime/Payment/Notification, chống trùng ghế, xử lý Payment/Notification sập, `GET /seats` |
| **Payment (TV5)** | Kiểm tra dữ liệu, chuẩn hóa giao dịch, 4 test gốc, báo cáo, sơ đồ | Envelope chung; `id` thay `_id`; 409 `ALREADY_PAID`; lọc `?bookingId=`; thêm 4 test HTTP; đọc `.env` |
| **Notification (TV6)** | Toàn bộ code Go, 2 file test, tài liệu, báo cáo, sơ đồ | Lỗi có `code`; hỗ trợ biến `PORT`; seed khớp seed chung (id 1, 2026-10-01 10:02) |

### Quyết định thiết kế
- Giữ envelope `status/data` (đã nằm trong Kế hoạch v2.1 và đã được 3/6 service dùng) thay vì `success: true`.
- Trạng thái đơn: `PENDING | PAID | CANCELLED` (khớp seed). `FAILED` chỉ dùng cho giao dịch Payment.
