-- Dữ liệu mẫu (khớp database/notification/seed.sql). Idempotent: INSERT OR IGNORE theo id, giữ nguyên id/giá trị cũ.
INSERT OR IGNORE INTO notification_logs (id, booking_id, username, channel, message, sent_at)
VALUES (1, 1, 'user1', 'EMAIL', 'Đặt vé thành công cho đơn #1', '2026-10-01T10:02:00Z');
