# Bản giữa kỳ của TV4 (chỉ để lưu trữ / tham khảo)

Đây là Booking Service **độc lập** nộp giữa kỳ (chưa gọi User/Movie/Showtime/Payment/Notification).
**Không chạy trong hệ thống tích hợp** — bản chính thức là `services/booking/`.

Giữ lại vì có các phần chưa nằm trong bản tích hợp:
- `src/BookingService.Tests/` — 12 test đơn vị (quy tắc ghế, bộ đọc request) + 17 test API;
- `docker-compose.yml` — MySQL riêng cho Booking (cổng 3307) để thử nhanh;
- `db/sqlserver/` — schema + seed SQL Server chạy lặp lại được; `DB_PROVIDER=sqlserver` trong `src/BookingService/Data/SqlDialect.cs`;
- `demo_api.ps1` — bản gốc dùng để chụp ảnh báo cáo (bản cập nhật cho API tích hợp: `scripts/demo-booking.ps1`).

Khác biệt API so với bản tích hợp: `POST` nhận `pricePerSeat` (tích hợp: giá lấy từ Showtime), ghế trùng trả 400 (tích hợp: 409 `SEAT_TAKEN`),
lỗi không có trường `code`. Vì vậy các test API ở đây sẽ không khớp bản tích hợp; muốn kiểm thử bản tích hợp dùng `tests/integration/run_tests.py`.
