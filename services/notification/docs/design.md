# Thiết kế TV6

Notification sở hữu database notification_db và bảng notification_logs: id INT PK AUTO_INCREMENT; booking_id INT NOT NULL; username VARCHAR(50) NOT NULL; channel VARCHAR(20) NOT NULL; message VARCHAR(255) NOT NULL; sent_at DATETIME NOT NULL. Database/bảng dùng utf8mb4, DATETIME quy ước UTC. Index sent_at/id phục vụ thứ tự đọc.

booking_id là FK **logic** đến Booking.bookings.id, không ràng buộc FOREIGN KEY hoặc truy vấn chéo database. Notification không xác thực sự tồn tại/trạng thái đơn ở giữa kỳ.

Actor: Booking Service dự kiến gửi POST, Admin đọc GET; trong demo giữa kỳ dùng PowerShell/Postman làm bên gửi. Luồng: nhận yêu cầu → kiểm tra JSON/dữ liệu → soạn nội dung → console sender giả lập → MySQL INSERT → JSON response. Khi sender/store lỗi trả 500. Luồng admin: fetch GET → kiểm tra response → bảng và lọc cục bộ.

Store interface chỉ có Insert/List, Sender chỉ có Send để thay fake trong HTTP test. Runtime duy nhất sử dụng MySQLStore, một sql.DB dùng chung. Không có chế độ stateless. Code cùng package main để chạy go run .

Đầu vào ERD: một entity notification_logs, booking_id đánh dấu tham chiếu ngoài hệ thống. Đầu vào Use Case: gửi thông báo giả lập, xem/lọc nhật ký. Đầu vào DFD: actor Booking/Admin, tiến trình validation/compose/simulate/persist, kho notification_db. Đây là mô tả đầu vào, chưa phải sơ đồ ERD/Use Case/DFD hoàn chỉnh.
