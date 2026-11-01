-- Schema SQLite của Notification Service. Idempotent: chạy lại nhiều lần an toàn, KHÔNG có DROP/DELETE.
-- Đối chiếu MySQL cũ: notification_db.notification_logs (database/notification/schema.sql).
CREATE TABLE IF NOT EXISTS notification_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    username   TEXT    NOT NULL,
    channel    TEXT    NOT NULL,
    message    TEXT    NOT NULL,
    sent_at    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sent_at_id ON notification_logs (sent_at, id);
