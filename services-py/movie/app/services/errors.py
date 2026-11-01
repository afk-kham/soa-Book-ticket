"""Ngoại lệ nghiệp vụ của Movie Service."""


class MovieServiceError(Exception):
    """Lỗi cơ sở của Movie Service."""


class MovieNotFoundError(MovieServiceError):
    """Không tìm thấy phim theo ID."""

    def __init__(self, movie_id: int):
        super().__init__(f"Không tìm thấy phim với ID = {movie_id}")
        self.movie_id = movie_id

