-- Dữ liệu mẫu ban đầu (Phụ lục A.1 Kế hoạch v2.1) + 10 phim bổ sung (khớp ui-seed/seed-movies.py) = 15 phim
-- Sử dụng INSERT OR IGNORE để không trùng lặp ID khi chạy lại
INSERT OR IGNORE INTO movies (id, title, genre, duration, poster, created_at) VALUES
(1, 'Avengers: Endgame', 'Hành động', 181, 'poster1.jpg', datetime('now', 'localtime')),
(2, 'Inception', 'Khoa học viễn tưởng', 148, 'poster2.jpg', datetime('now', 'localtime')),
(3, 'Parasite', 'Tâm lý', 132, 'poster3.jpg', datetime('now', 'localtime')),
(4, 'Mai', 'Tâm lý', 131, 'poster4.jpg', datetime('now', 'localtime')),
(5, 'Coco', 'Hoạt hình', 105, 'poster5.jpg', datetime('now', 'localtime')),
(6, 'Dune: Part Two', 'Khoa học viễn tưởng', 166, 'assets/posters/dune-part-two.jpg', datetime('now', 'localtime')),
(7, 'Despicable Me 4', 'Hoạt hình', 94, 'assets/posters/despicable-me-4.jpg', datetime('now', 'localtime')),
(8, 'Exhuma', 'Kinh dị', 134, 'assets/posters/exhuma.jpg', datetime('now', 'localtime')),
(9, 'Lật Mặt 7: Một Điều Ước', 'Gia đình', 138, 'assets/posters/lat-mat-7.jpg', datetime('now', 'localtime')),
(10, 'Kung Fu Panda 4', 'Hoạt hình', 94, 'assets/posters/kung-fu-panda-4.jpg', datetime('now', 'localtime')),
(11, 'Oppenheimer', 'Tâm lý', 180, 'assets/posters/oppenheimer.jpg', datetime('now', 'localtime')),
(12, 'Bỗng Dưng Trúng Số', 'Hài', 113, 'assets/posters/bong-dung-trung-so.jpg', datetime('now', 'localtime')),
(13, 'Spider-Man: Across the Spider-Verse', 'Hành động', 140, 'assets/posters/spider-man-across-the-spider-verse.jpg', datetime('now', 'localtime')),
(14, 'Nhà Bà Nữ', 'Gia đình', 102, 'assets/posters/nha-ba-nu.jpg', datetime('now', 'localtime')),
(15, 'Godzilla x Kong: The New Empire', 'Hành động', 115, 'assets/posters/godzilla-x-kong.jpg', datetime('now', 'localtime'));

