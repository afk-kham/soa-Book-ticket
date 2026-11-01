"""Repository của Movie Service: Tương tác trực tiếp với SQLite bằng câu lệnh SQL tham số hóa (?)."""
from typing import Any
from app.db.connection import get_connection
from app.entities.movie import Movie


class MovieRepository:
    def find_all(self) -> list[Movie]:
        """Lấy danh sách tất cả các bộ phim theo id tăng dần."""
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, title, genre, duration, poster, created_at FROM movies ORDER BY id ASC"
            )
            rows = cursor.fetchall()
            return [Movie.from_row(r) for r in rows]

    def find_by_id(self, movie_id: int) -> Movie | None:
        """Lấy thông tin một bộ phim theo ID."""
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, title, genre, duration, poster, created_at FROM movies WHERE id = ?",
                (movie_id,),
            )
            row = cursor.fetchone()
            return Movie.from_row(row) if row else None

    def create(self, title: str, genre: str | None = None, duration: int | None = None, poster: str | None = None) -> Movie:
        """Thêm phim mới vào CSDL và trả về Movie vừa tạo."""
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO movies (title, genre, duration, poster) VALUES (?, ?, ?, ?)",
                (title, genre, duration, poster),
            )
            new_id = cursor.lastrowid
            cursor = conn.execute(
                "SELECT id, title, genre, duration, poster, created_at FROM movies WHERE id = ?",
                (new_id,),
            )
            row = cursor.fetchone()
            return Movie.from_row(row)

    def update(
        self,
        movie_id: int,
        title: str | None = None,
        genre: str | None = None,
        duration: int | None = None,
        poster: str | None = None,
    ) -> Movie | None:
        """Cập nhật thông tin phim. Trả về Movie đã cập nhật hoặc None nếu không tìm thấy."""
        with get_connection() as conn:
            check = conn.execute("SELECT id FROM movies WHERE id = ?", (movie_id,)).fetchone()
            if not check:
                return None

            fields: list[str] = []
            values: list[Any] = []
            if title is not None:
                fields.append("title = ?")
                values.append(title)
            if genre is not None:
                fields.append("genre = ?")
                values.append(genre)
            if duration is not None:
                fields.append("duration = ?")
                values.append(duration)
            if poster is not None:
                fields.append("poster = ?")
                values.append(poster)

            if fields:
                values.append(movie_id)
                sql = f"UPDATE movies SET {', '.join(fields)} WHERE id = ?"
                conn.execute(sql, tuple(values))

            cursor = conn.execute(
                "SELECT id, title, genre, duration, poster, created_at FROM movies WHERE id = ?",
                (movie_id,),
            )
            row = cursor.fetchone()
            return Movie.from_row(row) if row else None

    def delete(self, movie_id: int) -> bool:
        """Xóa một bộ phim theo ID. Trả về True nếu xóa thành công, False nếu không tồn tại."""
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
            return cursor.rowcount > 0

