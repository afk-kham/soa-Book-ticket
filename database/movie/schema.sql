-- ========================================================
-- TV1: MOVIE SERVICE DATABASE SCHEMA
-- Hệ thống: Đặt vé xem phim Microservices (SOA)
-- CSDL: movie_db
-- Bảng: movies
-- ========================================================

CREATE DATABASE IF NOT EXISTS `movie_db` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `movie_db`;

DROP TABLE IF EXISTS `movies`;

CREATE TABLE `movies` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(255) NOT NULL COMMENT 'Tên phim',
    `genre` VARCHAR(100) DEFAULT NULL COMMENT 'Thể loại phim',
    `duration` INT DEFAULT NULL COMMENT 'Thời lượng phim tính bằng phút',
    `poster` VARCHAR(255) DEFAULT NULL COMMENT 'Tên file ảnh hoặc đường dẫn poster',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
