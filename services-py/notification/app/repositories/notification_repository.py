"""SQL SQLite cho notification_logs. Chỉ truy vấn tham số hóa (?), không có quy tắc nghiệp vụ."""
from app.db.connection import get_connection
from app.entities.notification_log import NotificationLog

_COLUMNS = "id, booking_id, username, channel, message, sent_at"
# Tên cột cho phép khi cập nhật (không bao giờ ghép chuỗi từ dữ liệu người dùng)
_UPDATABLE = ("booking_id", "username", "channel", "message")


def _row(r) -> NotificationLog:
    return NotificationLog(r["id"], r["booking_id"], r["username"], r["channel"], r["message"], r["sent_at"])


class NotificationRepository:
    def insert(self, booking_id: int, username: str, channel: str, message: str, sent_at: str) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO notification_logs (booking_id, username, channel, message, sent_at) VALUES (?,?,?,?,?)",
                (booking_id, username, channel, message, sent_at))
            return cur.lastrowid

    def list(self, booking_id: int | None = None, username: str | None = None,
             channel: str | None = None) -> list[NotificationLog]:
        where, args = [], []
        if booking_id is not None:
            where.append("booking_id = ?")
            args.append(booking_id)
        if username:
            where.append("LOWER(username) = LOWER(?)")
            args.append(username)
        if channel:
            where.append("channel = ?")
            args.append(channel)
        sql = f"SELECT {_COLUMNS} FROM notification_logs"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY sent_at DESC, id DESC"
        with get_connection() as conn:
            return [_row(r) for r in conn.execute(sql, args).fetchall()]

    def get(self, log_id: int) -> NotificationLog | None:
        with get_connection() as conn:
            r = conn.execute(f"SELECT {_COLUMNS} FROM notification_logs WHERE id = ?", (log_id,)).fetchone()
            return _row(r) if r else None

    def update(self, log_id: int, fields: dict) -> NotificationLog | None:
        """fields: khóa thuộc _UPDATABLE. Trả bản ghi sau cập nhật, None nếu không tồn tại."""
        cols = [c for c in _UPDATABLE if c in fields]
        with get_connection() as conn:
            if cols:
                cur = conn.execute(
                    "UPDATE notification_logs SET " + ", ".join(f"{c} = ?" for c in cols) + " WHERE id = ?",
                    [fields[c] for c in cols] + [log_id])
                if cur.rowcount == 0:
                    return None
            r = conn.execute(f"SELECT {_COLUMNS} FROM notification_logs WHERE id = ?", (log_id,)).fetchone()
            return _row(r) if r else None

    def delete(self, log_id: int) -> bool:
        with get_connection() as conn:
            return conn.execute("DELETE FROM notification_logs WHERE id = ?", (log_id,)).rowcount > 0
