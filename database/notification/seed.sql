-- notification_db — DỮ LIỆU MẪU DÙNG CHUNG (khớp seed/notification_db.sql của nhóm; chạy lại nhiều lần không trùng)
SET NAMES utf8mb4;
USE notification_db;
INSERT INTO notification_logs (id, booking_id, username, channel, message, sent_at)
VALUES (1, 1, 'user1', 'EMAIL', 'Đặt vé thành công cho đơn #1', '2026-10-01 10:02:00')
ON DUPLICATE KEY UPDATE id = id;
