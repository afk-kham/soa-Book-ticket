-- Booking Service (TV4) - du lieu mau, GIU NGUYEN id va gia tri cua database/booking/seed.sql (Phu luc A.4).
-- INSERT OR IGNORE: khong ghi de, khong xoa du lieu dang co. Chi chay khi duoc yeu cau:
--     python -m app.db.init_db --seed
INSERT OR IGNORE INTO bookings (id, movie_id, showtime_id, username, seats, total_price, status, created_at) VALUES
(1, 1, 1, 'user1', 'A1,A2', 180000, 'PAID',      '2026-10-01 10:00:00'),
(2, 2, 3, 'user2', 'B5',     85000, 'CANCELLED', '2026-10-01 11:00:00'),
(3, 4, 5, 'user1', 'C3,C4', 180000, 'PENDING',   '2026-10-02 09:30:00');
