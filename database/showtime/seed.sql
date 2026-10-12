-- showtime_db — DỮ LIỆU MẪU DÙNG CHUNG (KHÔNG đổi id/giá trị các dòng có sẵn)
SET NAMES utf8mb4;
USE showtime_db;
DELETE FROM showtimes;
INSERT INTO showtimes (id, movie_id, cinema, room, `time`, price) VALUES
(1, 1, 'CGV Vincom Đồng Khởi', 'P1', '2026-10-10 18:00:00', 90000),
(2, 1, 'CGV Vincom Đồng Khởi', 'P2', '2026-10-10 21:00:00', 100000),
(3, 2, 'Lotte Cinema Cantavil', 'P1', '2026-10-11 19:30:00', 85000),
(4, 3, 'BHD Star Bitexco', 'P3', '2026-10-11 20:00:00', 80000),
(5, 4, 'CGV Vincom Đồng Khởi', 'P3', '2026-10-12 17:30:00', 90000),
(6, 5, 'Lotte Cinema Cantavil', 'P2', '2026-10-12 15:00:00', 75000);
