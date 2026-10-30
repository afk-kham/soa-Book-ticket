-- User Service (TV3) - schema SQLite.
-- Idempotent: chi dung CREATE ... IF NOT EXISTS, KHONG co DROP/DELETE, KHONG nap du lieu.
-- Tuong thich schema MySQL cu (database/user/schema.sql): id, username, password_hash, email, role.
--   * username UNIQUE o muc DB (chong dang ky dong thoi).
--   * COLLATE NOCASE: MySQL cu dung utf8mb4_unicode_ci (khong phan biet hoa/thuong),
--     nen "Admin" va "admin" la cung mot tai khoan. Giu nguyen hanh vi nay.
--   * AUTOINCREMENT: id khong bao gio tai su dung (giong AUTO_INCREMENT).
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    email         TEXT,
    role          TEXT NOT NULL DEFAULT 'USER' CHECK (role IN ('USER', 'ADMIN')),
    CONSTRAINT uq_users_username UNIQUE (username)
);
