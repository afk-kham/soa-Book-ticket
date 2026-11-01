-- Dữ liệu mẫu ban đầu (Phụ lục A.1 Kế hoạch v2.1)
-- Sử dụng INSERT OR IGNORE để không trùng lặp ID khi chạy lại
INSERT OR IGNORE INTO movies (id, title, genre, duration, poster, created_at) VALUES
(1, 'Avengers: Endgame', 'Hành động', 181, 'poster1.jpg', datetime('now', 'localtime')),
(2, 'Inception', 'Khoa học viễn tưởng', 148, 'poster2.jpg', datetime('now', 'localtime')),
(3, 'Parasite', 'Tâm lý', 132, 'poster3.jpg', datetime('now', 'localtime')),
(4, 'Mai', 'Tâm lý', 131, 'poster4.jpg', datetime('now', 'localtime')),
(5, 'Coco', 'Hoạt hình', 105, 'poster5.jpg', datetime('now', 'localtime'));

