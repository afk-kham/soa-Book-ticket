# INTEGRATION_CHECKLIST — Danh sách kiểm tra trước khi gộp vào `develop` / `main`

Tích dấu từng mục. Nhóm trưởng chạy lại toàn bộ trước mỗi buổi demo.

## A. Từng service (người sở hữu tự kiểm tra)
- [ ] Chạy đúng cổng trong `API_CONTRACT.md`; đọc cấu hình từ `.env` (có `.env.example`)
- [ ] Dùng đúng tên CSDL; `schema.sql` + `seed.sql` nạp được trên máy trống, nạp lại không lỗi
- [ ] Mọi response theo envelope `status/data` hoặc `status/code/message`
- [ ] Tên trường JSON camelCase, không lộ cột snake_case, mật khẩu, `_id`, chi tiết lỗi SQL
- [ ] `OPTIONS` trả 204 + header CORS; `Access-Control-Allow-Origin: *`
- [ ] Sai dữ liệu → 400; không tìm thấy → 404; sai method → 405; không bao giờ crash khi body rỗng/sai JSON
- [ ] Có `README.md` trong thư mục service: cách cài, chạy, test
- [ ] Không có mật khẩu/`.env` trong commit

## B. Giao diện
- [ ] Trang Admin của service mình dùng khung chung (`Admin.shell`), không CSS riêng
- [ ] Service tắt → trang hiện thông báo "Service ... đang không chạy", không trắng trang
- [ ] Thêm / sửa / xóa (nếu có) hoạt động và tải lại danh sách

## C. Tích hợp (chạy `python tests/integration/run_tests.py` → 0 lỗi)
- [ ] Đặt vé thành công: đơn PAID, có giao dịch ở Payment, có nhật ký ở Notification
- [ ] Đặt ghế đã có người → 409
- [ ] Thanh toán thất bại → đơn CANCELLED, ghế được nhả
- [ ] Tắt Payment → 503, không treo; tắt Notification → đơn vẫn PAID; tắt Showtime/User → 503
- [ ] Client: đăng ký → đăng nhập → chọn phim → chọn ghế → đặt vé → thấy trong "Vé của tôi"

## D. Tài liệu & demo
- [ ] Báo cáo, ERD, Use Case, DFD của từng người trong `docs/tvN-*/`
- [ ] Mỗi người trả lời được: service mình gọi ai, ai gọi mình, khi đối tác sập thì sao
- [ ] Chạy demo từ máy sạch theo `README.md` trong ≤ 10 phút
