# CHANGELOG

## Poster, thanh toán chuyển khoản, xử lý đơn chờ, vé điện tử, lịch chiếu cập nhật liên tục
Chi tiết và lý do từng thay đổi: [`docs/REVIEW_CAI_TIEN_DAT_VE.md`](docs/REVIEW_CAI_TIEN_DAT_VE.md).

- **Client**: poster thật (`client/img/posters/`), luồng *chọn ghế → giữ ghế 10 phút → trang thanh toán (VietQR / MoMo / VNPAY) → vé điện tử có mã QR*; "Vé của tôi" có đếm ngược, nút Thanh toán/Hủy cho đơn chờ, nút Xem vé cho đơn đã trả; lịch chiếu và sơ đồ ghế tự cập nhật; bỏ thuật ngữ kỹ thuật khỏi giao diện và thông báo lỗi. Mã QR sinh ngay trên trình duyệt (`js/qr.js`, không cần mạng).
- **Booking**: `payNow:false` (giữ ghế), `POST /api/booking/{id}/pay`, `POST /api/booking/{id}/cancel`, `GET /api/booking/availability`, trường `expiresAt`, tự hủy đơn quá hạn (`HOLD_MINUTES`), từ chối suất đã chiếu (`SHOWTIME_CLOSED`); gọi service khác ưu tiên IPv4 (mỗi lời gọi nhanh hơn ~1 giây trên Windows); `created_at` ghi theo giờ máy Booking.
- **Showtime**: tự xếp lịch 7 ngày tới (`AUTO_SCHEDULE_DAYS`), lọc `?upcoming=1`, đặt múi giờ `APP_TIMEZONE`.
- **Payment**: thêm phương thức `BANK_TRANSFER`.
- **Admin**: bỏ cổng / tên CSDL / công nghệ / mã thành viên khỏi giao diện; poster thật ở trang Phim; nhãn tiếng Việt cho phương thức và kết quả thanh toán; "Đặt vé thử" thành "Bán vé tại quầy".
- **Test tích hợp**: chọn suất sắp chiếu thay vì `shows[0]`; thêm nhóm [7] cho luồng giữ ghế / thanh toán sau / hủy (54 kiểm tra).

## Sửa script chạy User Service
- `mvn exec:java` chạy app trong classloader riêng nên JDBC báo `No suitable driver` (gặp với Maven 3.10 + JDK 21). `start-all.bat` gọi `scripts/run-user.bat` (Maven chỉ build classpath, chạy bằng `java`); `start-all.sh` làm tương tự. Không đổi code `services/user/`.

## Giao diện hoàn chỉnh — Client & Admin
Chỉ sửa `client/` và `admin/`; **không** đổi API, CSDL hay code service. Vẫn là HTML/CSS/JS thuần, không cần build.

### Client (`client/`)
- Trang chủ: phim nổi bật, tìm kiếm theo tên, lọc theo thể loại, số suất chiếu của từng phim; ảnh bìa tự sinh theo tên phim (dùng ảnh thật nếu `poster` là URL).
- Chi tiết phim: lịch chiếu chia theo ngày, nhóm theo rạp, hiện giá từng suất.
- Chọn ghế: sơ đồ 6×10 có lối đi (cấu hình `SEAT_MAP` trong `js/config.js`), bảng tóm tắt, chọn phương thức thanh toán; gặp `SEAT_TAKEN` thì tự tải lại sơ đồ.
- Kết quả dạng vé (mã đơn, giao dịch, trạng thái thông báo); "Vé của tôi" có tab lọc theo trạng thái, kèm tên phim/rạp/giờ chiếu.
- Đăng nhập/đăng ký: kiểm tra dữ liệu, hiện/ẩn mật khẩu, nút điền nhanh tài khoản thử. Có trạng thái đang tải, lỗi service sập (kèm nút thử lại), giao diện điện thoại.

### Admin (`admin/`)
- Khung chung mới: thanh bên có biểu tượng và chấm trạng thái từng service, menu trên điện thoại, chế độ tối theo hệ điều hành.
- `common.js` giữ nguyên mọi hàm cũ, thêm: tìm kiếm trong bảng (`table(..., opts)`), `stats`, `drawer`, `dl`, `confirmBox` (hộp xác nhận thay `window.confirm`), `loading`, `tryApi`, `ping`, `thumb`, `seats`.
- Tổng quan: số liệu tổng (phim, suất chiếu, người dùng, đơn, doanh thu), sức khỏe 6 service (công nghệ, CSDL, độ trễ), đơn gần đây, tỉ lệ trạng thái đơn.
- Đặt vé: thống kê theo trạng thái; bấm vào một đơn để xem chi tiết ghép từ Booking + Payment + Notification (vẫn hiện được khi một service sập).
- Các trang còn lại có ô thống kê, tìm kiếm, lọc phim (Suất chiếu), nút làm mới.

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
