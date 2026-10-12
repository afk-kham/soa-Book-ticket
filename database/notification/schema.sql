-- Tạo mới an toàn; không thay đổi cấu trúc bảng đã tồn tại.
CREATE DATABASE IF NOT EXISTS notification_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE notification_db;
CREATE TABLE IF NOT EXISTS notification_logs (
 id INT PRIMARY KEY AUTO_INCREMENT,
 booking_id INT NOT NULL,
 username VARCHAR(50) NOT NULL,
 channel VARCHAR(20) NOT NULL,
 message VARCHAR(255) NOT NULL,
 sent_at DATETIME NOT NULL,
 INDEX idx_sent_at_id (sent_at, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
