"""Dữ liệu nội bộ của một dòng notification_logs (snake_case, khớp cột SQLite)."""
from dataclasses import dataclass


@dataclass
class NotificationLog:
    id: int
    booking_id: int
    username: str
    channel: str
    message: str
    sent_at: str  # ISO-8601 UTC "YYYY-MM-DDTHH:MM:SSZ"
