"""Entity Movie: Đại diện cho cấu trúc dữ liệu lưu trữ nội bộ (snake_case)."""
from dataclasses import dataclass
import sqlite3
from typing import Any


@dataclass
class Movie:
    id: int | None
    title: str
    genre: str | None = None
    duration: int | None = None
    poster: str | None = None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Movie":
        return cls(
            id=row["id"],
            title=row["title"],
            genre=row["genre"],
            duration=row["duration"],
            poster=row["poster"],
            created_at=str(row["created_at"]) if row["created_at"] else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "genre": self.genre,
            "duration": self.duration,
            "poster": self.poster,
            "created_at": self.created_at,
        }

