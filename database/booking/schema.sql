-- booking_db — SCHEMA (sở hữu bởi service tương ứng, không service nào khác được truy cập)
CREATE DATABASE IF NOT EXISTS booking_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE booking_db;

DROP TABLE IF EXISTS bookings;
CREATE TABLE bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  movie_id INT NOT NULL,          -- FK logic -> Movie
  showtime_id INT NOT NULL,       -- FK logic -> Showtime
  username VARCHAR(50) NOT NULL,  -- FK logic -> User
  seats VARCHAR(100) NOT NULL,    -- ví dụ 'A1,A2'
  total_price INT NOT NULL,
  status VARCHAR(10) NOT NULL DEFAULT 'PENDING',   -- PENDING | PAID | CANCELLED
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  -- (bổ sung từ TV4) chỉ mục cho truy vấn ghế đã giữ theo suất chiếu / lọc theo người đặt
  KEY idx_bookings_showtime_status (showtime_id, status),
  KEY idx_bookings_username (username),
  -- (bổ sung từ TV4) ràng buộc trạng thái và tổng tiền ngay tại CSDL
  CONSTRAINT chk_bookings_status CHECK (status IN ('PENDING', 'PAID', 'CANCELLED')),
  CONSTRAINT chk_bookings_total CHECK (total_price >= 0)
);
