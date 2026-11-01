-- User Service (TV3) - du lieu mau, GIU NGUYEN id va hash cua database/user/seed.sql (khop Phu luc A.3).
-- Admin@123 -> hash thu nhat | User@123 -> hash thu hai (KHONG tu sinh hash khac).
-- INSERT OR IGNORE: khong ghi de, khong xoa du lieu dang co. Chi chay khi duoc yeu cau:
--     python -m app.db.seed
INSERT OR IGNORE INTO users (id, username, password_hash, email, role) VALUES
(1, 'admin', '$2a$10$E8cofqiolfZk1ihu2plZM.UJfIuTvkB54LjgTxFBmeJwpY59Z/yju', 'admin@cinema.local', 'ADMIN'),
(2, 'user1', '$2a$10$ItvF/UzunDkYLpvNquq4iOP9vu4Z/gL0eoX3.FBvC1UaNSa2ugQ6O', 'user1@cinema.local', 'USER'),
(3, 'user2', '$2a$10$ItvF/UzunDkYLpvNquq4iOP9vu4Z/gL0eoX3.FBvC1UaNSa2ugQ6O', 'user2@cinema.local', 'USER');
