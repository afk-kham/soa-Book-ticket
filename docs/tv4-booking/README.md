# Tài liệu TV4 — Booking
Đặt tại đây: ERD, Use Case, DFD 0/1/2, báo cáo của TV4.
Gợi ý nội dung: luồng điều phối ở `INTEGRATION_FLOW.md` (sơ đồ tuần tự + bảng xử lý lỗi) là tư liệu chính cho DFD mức 1 và mức 2 của Booking.

## Sản phẩm của TV4 (đã gộp vào Baseline V2)
| Sản phẩm | Tệp |
|---|---|
| P2 ERD | `ERD_booking.png`, `ERD_booking.drawio` |
| P3 Use Case | `UC_booking.png`, `UC_booking.drawio` |
| P4 DFD mức 0, 1 | `DFD0_booking.png`, `DFD1_booking.png` (+ `.drawio`) |
| P5 DFD mức 2 | `DFD2_booking.png`, `DFD2_booking.drawio` |
| P8 Báo cáo chức năng | `05_baocao_booking.docx` (bản PDF: `reports/05_baocao_booking.pdf`) |
| Ảnh kết quả chạy | `anh-ket-qua/` (T1–T7, giao diện admin) |
| Giao diện admin giữa kỳ (tham khảo) | `admin_booking_giua_ky.html` |
| Mã nguồn + test giữa kỳ (bản độc lập) | `source-giua-ky/` |

**Lưu ý:** báo cáo và ảnh kết quả mô tả bản **giữa kỳ** (Booking chạy độc lập, `POST /api/booking` nhận `pricePerSeat`).
Bản dùng để tích hợp là `services/booking/` (điều phối User/Movie/Showtime/Payment/Notification, giá lấy từ Showtime) — xem `INTEGRATION_FLOW.md`.
Trang admin dùng trong hệ thống là `admin/pages/booking.html` (dùng khung chung); `admin_booking_giua_ky.html` chỉ giữ để tham khảo
(có thêm: đếm theo trạng thái, tìm theo người đặt/mã đơn/ghế, tổng tiền đã thanh toán, ngăn chi tiết đơn).
