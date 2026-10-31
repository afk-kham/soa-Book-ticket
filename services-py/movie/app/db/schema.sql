-- Schema SQLite cho Movie Service
-- Đảm bảo tính lũy thừa (idempotent), không DROP dữ liệu
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    genre TEXT,
    duration INTEGER,
    poster TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

