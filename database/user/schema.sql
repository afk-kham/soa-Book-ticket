-- ============================================================
-- TV3 - User/Auth Service | CSDL user_db (MySQL 8 / MariaDB 10.x)
-- Chay: mysql -u root -p < schema.sql
-- ============================================================
DROP DATABASE IF EXISTS user_db;
CREATE DATABASE user_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE user_db;

CREATE TABLE users (
    id            INT          NOT NULL AUTO_INCREMENT,
    username      VARCHAR(50)  NOT NULL,
    password_hash VARCHAR(100) NOT NULL COMMENT 'BCrypt, tien to $2a$',
    email         VARCHAR(100) NULL,
    role          VARCHAR(10)  NOT NULL DEFAULT 'USER' COMMENT 'USER hoac ADMIN',
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
