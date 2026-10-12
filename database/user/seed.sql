-- ============================================================
-- Du lieu mau - khop Phu luc A.3 cua Ke hoach v2.1
-- Admin@123 -> hash thu nhat | User@123 -> hash thu hai (KHONG tu sinh hash khac)
-- Chay: mysql -u root -p < seed.sql   (sau khi chay schema.sql)
-- ============================================================
USE user_db;
SET NAMES utf8mb4;

INSERT INTO users (id, username, password_hash, email, role) VALUES
(1, 'admin', '$2a$10$E8cofqiolfZk1ihu2plZM.UJfIuTvkB54LjgTxFBmeJwpY59Z/yju', 'admin@cinema.local', 'ADMIN'),
(2, 'user1', '$2a$10$ItvF/UzunDkYLpvNquq4iOP9vu4Z/gL0eoX3.FBvC1UaNSa2ugQ6O', 'user1@cinema.local', 'USER'),
(3, 'user2', '$2a$10$ItvF/UzunDkYLpvNquq4iOP9vu4Z/gL0eoX3.FBvC1UaNSa2ugQ6O', 'user2@cinema.local', 'USER');

ALTER TABLE users AUTO_INCREMENT = 4;
