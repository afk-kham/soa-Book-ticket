"""Repository: mọi câu SQL của Booking (tham số hóa bằng ?). Không chứa quy tắc nghiệp vụ."""
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.db.connection import get_connection
from app.entities import CANCELLED, PENDING, Booking

_COLUMNS = "id, movie_id, showtime_id, username, seats, total_price, status, created_at"


def _split_seats(seats: str) -> list[str]:
    return [seat.strip() for seat in seats.split(",") if seat.strip()]


def _to_entity(row: sqlite3.Row) -> Booking:
    return Booking(
        id=row["id"],
        movie_id=row["movie_id"],
        showtime_id=row["showtime_id"],
        username=row["username"],
        seats=_split_seats(row["seats"]),
        total_price=row["total_price"],
        status=row["status"],
        created_at=row["created_at"],
    )


class BookingRepository:
    def __init__(self, conn: sqlite3.Connection | None = None):
        self._conn = conn

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        if self._conn is not None:
            yield self._conn
        else:
            with get_connection() as conn:
                yield conn

    @contextmanager
    def transaction(self) -> Iterator["BookingRepository"]:
        """Giao dịch ghi BEGIN IMMEDIATE: giành quyền ghi ngay từ đầu nên "đọc rồi ghi" là nguyên tử (D-10)."""
        with get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            yield BookingRepository(conn)

    def ping(self) -> None:
        with self._connection() as conn:
            conn.execute("SELECT 1").fetchone()

    def find_all(self, username: str | None, status: str | None, showtime_id: int | None) -> list[Booking]:
        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT {_COLUMNS} FROM bookings
                WHERE (:username IS NULL OR username = :username)
                  AND (:status IS NULL OR status = :status)
                  AND (:showtime_id IS NULL OR showtime_id = :showtime_id)
                ORDER BY id
                """,
                {"username": username, "status": status, "showtime_id": showtime_id},
            ).fetchall()
        return [_to_entity(row) for row in rows]

    def get(self, booking_id: int) -> Booking | None:
        with self._connection() as conn:
            row = conn.execute(f"SELECT {_COLUMNS} FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        return _to_entity(row) if row else None

    def taken_seats(self, showtime_id: int) -> set[str]:
        """Ghế đang bị giữ của một suất: đơn CANCELLED không giữ ghế."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT seats FROM bookings WHERE showtime_id = ? AND status <> ?",
                (showtime_id, CANCELLED),
            ).fetchall()
        return {seat for row in rows for seat in _split_seats(row["seats"])}

    def taken_counts(self, showtime_ids: list[int]) -> dict[int, int]:
        """Số ghế đang bị giữ của nhiều suất, giữ thứ tự id truyền vào, bỏ id trùng."""
        counts = dict.fromkeys(showtime_ids, 0)
        placeholders = ", ".join("?" for _ in counts)
        with self._connection() as conn:
            rows = conn.execute(
                f"SELECT showtime_id, seats FROM bookings WHERE status <> ? AND showtime_id IN ({placeholders})",
                (CANCELLED, *counts),
            ).fetchall()
        for row in rows:
            counts[row["showtime_id"]] += len(_split_seats(row["seats"]))
        return counts

    def insert_pending(
        self, movie_id: int, showtime_id: int, username: str, seats: list[str], total_price: int, created_at: str
    ) -> Booking:
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO bookings (movie_id, showtime_id, username, seats, total_price, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (movie_id, showtime_id, username, ",".join(seats), total_price, PENDING, created_at),
            )
            row = conn.execute(f"SELECT {_COLUMNS} FROM bookings WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return _to_entity(row)

    def update_status(self, booking_id: int, status: str) -> None:
        with self._connection() as conn:
            conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))

    def update_seats(self, booking_id: int, seats: list[str], total_price: int) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE bookings SET seats = ?, total_price = ? WHERE id = ?",
                (",".join(seats), total_price, booking_id),
            )

    def delete(self, booking_id: int) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))

    def try_update_status(self, booking_id: int, current: str, new: str) -> bool:
        """Đổi trạng thái chỉ khi đơn đang ở ``current`` (tránh ghi đè khi hai yêu cầu chạy song song)."""
        with self._connection() as conn:
            cursor = conn.execute(
                "UPDATE bookings SET status = ? WHERE id = ? AND status = ?", (new, booking_id, current)
            )
            return cursor.rowcount > 0

    def expire_pending(self, cutoff: str) -> int:
        """Hủy các đơn PENDING tạo trước ``cutoff``. Trả về số đơn bị hủy."""
        with self._connection() as conn:
            cursor = conn.execute(
                "UPDATE bookings SET status = ? WHERE status = ? AND created_at < ?",
                (CANCELLED, PENDING, cutoff),
            )
            return cursor.rowcount
