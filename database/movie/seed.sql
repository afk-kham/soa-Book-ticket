-- ========================================================
-- TV1: MOVIE SERVICE SEED DATA (Phụ lục A.1 Kế hoạch v2.1)
-- Lưu ý: Giữ đúng ID 1-5 để khớp với các service khác trong hệ thống!
-- ========================================================

SET NAMES utf8mb4;
USE `movie_db`;

-- Xóa dữ liệu cũ nếu có
DELETE FROM `movies`;
ALTER TABLE `movies` AUTO_INCREMENT = 1;

-- Nạp 5 bộ phim theo Phụ lục A.1
INSERT INTO `movies` (`id`, `title`, `genre`, `duration`, `poster`) VALUES
(1, 'Avengers: Endgame', 'Hành động', 181, 'poster1.jpg'),
(2, 'Inception', 'Khoa học viễn tưởng', 148, 'poster2.jpg'),
(3, 'Parasite', 'Tâm lý', 132, 'poster3.jpg'),
(4, 'Mai', 'Tâm lý', 131, 'poster4.jpg'),
(5, 'Coco', 'Hoạt hình', 105, 'poster5.jpg');
