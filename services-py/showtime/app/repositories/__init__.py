"""Parameterized SQLite persistence operations for showtimes."""

import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime

from app.db.connection import get_connection
from app.entities import Showtime


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS showtimes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id INTEGER NOT NULL,
    cinema TEXT NOT NULL,
    room TEXT NOT NULL,
    time TEXT NOT NULL,
    price INTEGER NOT NULL
)
"""
_UPDATE_COLUMNS = {
    "movie_id": "movie_id",
    "cinema": "cinema",
    "room": "room",
    "time": "time",
    "price": "price",
}


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(_CREATE_TABLE)


def _to_entity(row: sqlite3.Row | None) -> Showtime | None:
    if row is None:
        return None
    return Showtime(
        id=row["id"],
        movie_id=row["movie_id"],
        cinema=row["cinema"],
        room=row["room"],
        time=row["time"],
        price=row["price"],
    )


def create_showtime(
    movie_id: int, cinema: str, room: str, showtime: str, price: int
) -> Showtime:
    with get_connection() as connection:
        _ensure_schema(connection)
        cursor = connection.execute(
            "INSERT INTO showtimes (movie_id, cinema, room, time, price) "
            "VALUES (?, ?, ?, ?, ?)",
            (movie_id, cinema, room, showtime, price),
        )
        connection.commit()
        row = connection.execute(
            "SELECT id, movie_id, cinema, room, time, price "
            "FROM showtimes WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    entity = _to_entity(row)
    if entity is None:
        raise RuntimeError("Inserted showtime could not be read")
    return entity


def get_showtime(showtime_id: int) -> Showtime | None:
    with get_connection() as connection:
        _ensure_schema(connection)
        row = connection.execute(
            "SELECT id, movie_id, cinema, room, time, price "
            "FROM showtimes WHERE id = ?",
            (showtime_id,),
        ).fetchone()
    return _to_entity(row)


def list_showtimes(
    movie_id: int | None = None, upcoming_after: str | None = None
) -> list[Showtime]:
    clauses: list[str] = []
    parameters: list[object] = []
    if movie_id is not None:
        clauses.append("movie_id = ?")
        parameters.append(movie_id)
    if upcoming_after is not None:
        clauses.append("time > ?")
        parameters.append(upcoming_after)
    where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection() as connection:
        _ensure_schema(connection)
        rows = connection.execute(
            "SELECT id, movie_id, cinema, room, time, price FROM showtimes"
            f"{where_clause} ORDER BY time, id",
            parameters,
        ).fetchall()
    return [entity for row in rows if (entity := _to_entity(row)) is not None]


def update_showtime(showtime_id: int, changes: Mapping[str, object]) -> Showtime | None:
    columns = [(key, _UPDATE_COLUMNS[key]) for key in changes]
    assignments = ", ".join(f"{column} = ?" for _, column in columns)
    values = [changes[key] for key, _ in columns]
    with get_connection() as connection:
        _ensure_schema(connection)
        connection.execute(
            f"UPDATE showtimes SET {assignments} WHERE id = ?",
            (*values, showtime_id),
        )
        connection.commit()
        row = connection.execute(
            "SELECT id, movie_id, cinema, room, time, price "
            "FROM showtimes WHERE id = ?",
            (showtime_id,),
        ).fetchone()
    return _to_entity(row)


def delete_showtime(showtime_id: int) -> bool:
    with get_connection() as connection:
        _ensure_schema(connection)
        cursor = connection.execute(
            "DELETE FROM showtimes WHERE id = ?", (showtime_id,)
        )
        connection.commit()
    return cursor.rowcount > 0


def list_movie_ids() -> list[int]:
    with get_connection() as connection:
        _ensure_schema(connection)
        rows = connection.execute(
            "SELECT DISTINCT movie_id FROM showtimes ORDER BY movie_id"
        ).fetchall()
    return [row["movie_id"] for row in rows]


def get_scheduled_days(start: datetime, end: datetime) -> set[str]:
    with get_connection() as connection:
        _ensure_schema(connection)
        rows = connection.execute(
            "SELECT DISTINCT date(time) AS show_date FROM showtimes "
            "WHERE time >= ? AND time < ?",
            (start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")),
        ).fetchall()
    return {row["show_date"] for row in rows if row["show_date"] is not None}


class ScheduleTransaction:
    """SQL-only operations on a transaction held by the repository."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_scheduled_days(self, start: datetime, end: datetime) -> set[str]:
        rows = self._connection.execute(
            "SELECT DISTINCT date(time) AS show_date FROM showtimes "
            "WHERE time >= ? AND time < ?",
            (
                start.strftime("%Y-%m-%d %H:%M:%S"),
                end.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        ).fetchall()
        return {row["show_date"] for row in rows if row["show_date"] is not None}

    def insert_showtimes(
        self, rows: Sequence[tuple[int, str, str, str, int]]
    ) -> None:
        if not rows:
            return
        self._connection.executemany(
            "INSERT INTO showtimes (movie_id, cinema, room, time, price) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )


@contextmanager
def schedule_transaction() -> Iterator[ScheduleTransaction]:
    with get_connection() as connection:
        _ensure_schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        try:
            yield ScheduleTransaction(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
