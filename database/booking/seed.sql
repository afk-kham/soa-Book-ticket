-- booking_db — DỮ LIỆU MẪU DÙNG CHUNG (KHÔNG đổi id/giá trị các dòng có sẵn)
SET NAMES utf8mb4;
USE booking_db;
DELETE FROM bookings;
INSERT INTO bookings (id, movie_id, showtime_id, username, seats, total_price, status, created_at) VALUES
(1, 1, 1, 'user1', 'A1,A2', 180000, 'PAID',      '2026-10-01 10:00:00'),
(2, 2, 3, 'user2', 'B5',     85000, 'CANCELLED', '2026-10-01 11:00:00'),
(3, 4, 5, 'user1', 'C3,C4', 180000, 'PENDING',   '2026-10-02 09:30:00');
