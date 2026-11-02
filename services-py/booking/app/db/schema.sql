-- Booking Service (TV4) - schema SQLite.
-- Idempotent: chi dung CREATE ... IF NOT EXISTS, KHONG co DROP/DELETE, KHONG nap du lieu.
-- Tuong thich schema MySQL cu (database/booking/schema.sql): cung cot, cung 2 chi muc, cung 2 CHECK.
--   * movie_id, showtime_id, username la tham chieu logic (khong co khoa ngoai xuyen service).
--   * username COLLATE NOCASE: MySQL cu dung utf8mb4_unicode_ci nen loc ?username= khong phan biet
--     hoa/thuong; giong cot users.username cua User Service.
--   * seats luu dang 'A1,A2'; created_at luu TEXT 'YYYY-MM-DD HH:MM:SS' do service ghi.
--   * AUTOINCREMENT: id don khong bao gio tai su dung (Payment/Notification luu lai id nay).
CREATE TABLE IF NOT EXISTS bookings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id    INTEGER NOT NULL,
    showtime_id INTEGER NOT NULL,
    username    TEXT    NOT NULL COLLATE NOCASE,
    seats       TEXT    NOT NULL,
    total_price INTEGER NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'PENDING',
    created_at  TEXT    NOT NULL,
    CONSTRAINT chk_bookings_status CHECK (status IN ('PENDING', 'PAID', 'CANCELLED')),
    CONSTRAINT chk_bookings_total CHECK (total_price >= 0)
);

CREATE INDEX IF NOT EXISTS idx_bookings_showtime_status ON bookings (showtime_id, status);
CREATE INDEX IF NOT EXISTS idx_bookings_username ON bookings (username);
