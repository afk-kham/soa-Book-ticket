-- showtime_db — SCHEMA (sở hữu bởi service tương ứng, không service nào khác được truy cập)
CREATE DATABASE IF NOT EXISTS showtime_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE showtime_db;

DROP TABLE IF EXISTS showtimes;
CREATE TABLE showtimes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  movie_id INT NOT NULL,            -- FK logic -> movie_db.movies.id (KHÔNG tạo FOREIGN KEY thật)
  cinema VARCHAR(150),
  room VARCHAR(50),
  `time` DATETIME,
  price INT
);
