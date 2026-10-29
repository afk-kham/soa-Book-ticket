-- =====================================================================
-- Booking Service (TV4 - C#) - P1: Lược đồ CSDL booking_db
-- Dùng cho MySQL 8.0+ (hoặc MariaDB 10.4+).
--
-- Chạy lặp lại nhiều lần được: chỉ CREATE ... IF NOT EXISTS,
-- không DROP / TRUNCATE nên không làm mất đơn đã có.
--
-- Nguyên tắc database-per-service: movie_id, showtime_id, username
-- chỉ là khóa ngoại LOGIC sang Movie / Showtime / User Service,
-- KHÔNG tạo FOREIGN KEY vật lý.
-- =====================================================================

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS booking_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE booking_db;

CREATE TABLE IF NOT EXISTS bookings (
  id          INT          NOT NULL AUTO_INCREMENT,
  movie_id    INT          NOT NULL COMMENT 'FK logic -> Movie.movies.id',
  showtime_id INT          NOT NULL COMMENT 'FK logic -> Showtime.showtimes.id',
  username    VARCHAR(50)  NOT NULL COMMENT 'FK logic -> User.users.username',
  seats       VARCHAR(100) NOT NULL COMMENT 'Danh sách ghế, ví dụ A1,A2',
  total_price INT          NOT NULL COMMENT 'Số ghế x giá vé (VND)',
  `status`    VARCHAR(10)  NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING | PAID | CANCELLED',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm tạo đơn',
  PRIMARY KEY (id),
  -- Hỗ trợ truy vấn kiểm tra ghế trùng theo suất chiếu
  KEY idx_bookings_showtime_status (showtime_id, `status`),
  KEY idx_bookings_username (username),
  CONSTRAINT chk_bookings_status CHECK (`status` IN ('PENDING', 'PAID', 'CANCELLED')),
  CONSTRAINT chk_bookings_total  CHECK (total_price >= 0)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
