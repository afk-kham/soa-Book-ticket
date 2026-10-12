-- =====================================================================
-- Booking Service (TV4 - C#) - P1: Dữ liệu mẫu booking_db
-- Khớp Phụ lục A.4 của Kế hoạch v2.1 và file chung seed/booking_db.sql.
--
-- Chạy SAU schema.sql. Chạy lặp lại được:
--   REPLACE INTO chỉ ghi đè đúng 3 dòng id 1-3 về giá trị chuẩn,
--   các đơn tạo thêm (id >= 4) được giữ nguyên.
-- Không đổi id và giá trị của các dòng mẫu (quy ước chung của nhóm).
-- =====================================================================

SET NAMES utf8mb4;

USE booking_db;

REPLACE INTO bookings (id, movie_id, showtime_id, username, seats, total_price, `status`, created_at) VALUES
(1, 1, 1, 'user1', 'A1,A2', 180000, 'PAID',      '2026-10-01 10:00:00'),
(2, 2, 3, 'user2', 'B5',     85000, 'CANCELLED', '2026-10-01 11:00:00'),
(3, 4, 5, 'user1', 'C3,C4', 180000, 'PENDING',   '2026-10-02 09:30:00');

-- Kiểm tra nhanh
SELECT id, movie_id, showtime_id, username, seats, total_price, `status`, created_at
FROM bookings
ORDER BY id;
