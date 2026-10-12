# Kế hoạch cuối kỳ — CHƯA TRIỂN KHAI

- POST /api/notify kiểm tra X-Internal-Key; khóa chỉ ở server, không đưa vào JavaScript admin.
- GET /api/notify/logs kiểm tra JWT ADMIN: HS256, secret môi trường theo byte UTF-8, claims sub/userId/role/iat/exp; thống nhất với TV3 và kiểm tra chữ ký/hết hạn/role.
- Booking gọi với timeout sau PAID; lỗi Notification không hủy đơn PAID. Thanh toán thất bại không gọi Notification.
- Thêm requestId/idempotency key và UNIQUE constraint để retry không tạo thông báo trùng, thống nhất response khi gọi lại.
- Trạng thái xử lý, retry bền vững; queue/outbox nếu nhóm chọn mở rộng. Giải quyết khoảng trống giữa gửi và lưu log.
- Chuyển cấu trúc sang cmd/notification và internal/{handler,store,middleware,...}.
- Nếu gửi email/SMS thật: bổ sung thông tin người nhận và tích hợp nhà cung cấp theo hợp đồng mới.
- Ghép 5 trang admin còn lại và báo cáo tổng quan khi nhận đủ tài liệu của nhóm.

Bản giữa kỳ hiện không bật các cơ chế bảo mật/tích hợp này. Phương án Notification dùng CSDL vẫn chờ giảng viên xác nhận; store đã tách để dễ điều chỉnh sau.
