"""Internal snake_case representation of a SQLite showtime row."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Showtime:
    id: int
    movie_id: int
    cinema: str
    room: str
    time: str
    price: int
