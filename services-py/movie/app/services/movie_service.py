"""Service của Movie Service: Xử lý logic nghiệp vụ, độc lập với tầng HTTP/FastAPI."""
from app.entities.movie import Movie
from app.repositories.movie_repository import MovieRepository
from app.schemas.movie import MovieCreate, MovieUpdate
from app.services.errors import MovieNotFoundError


class MovieService:
    def __init__(self, repository: MovieRepository):
        self._repo = repository

    def list_movies(self) -> list[Movie]:
        """Lấy danh sách tất cả phim."""
        return self._repo.find_all()

    def get_movie(self, movie_id: int) -> Movie:
        """Lấy chi tiết một phim theo ID. Ném MovieNotFoundError nếu không tồn tại."""
        movie = self._repo.find_by_id(movie_id)
        if not movie:
            raise MovieNotFoundError(movie_id)
        return movie

    def create_movie(self, data: MovieCreate) -> Movie:
        """Thêm phim mới sau khi đã validate dữ liệu."""
        return self._repo.create(
            title=data.title,
            genre=data.genre,
            duration=data.duration,
            poster=data.poster,
        )

    def update_movie(self, movie_id: int, data: MovieUpdate) -> Movie:
        """Cập nhật thông tin phim. Ném MovieNotFoundError nếu phim không tồn tại."""
        updated = self._repo.update(
            movie_id=movie_id,
            title=data.title,
            genre=data.genre,
            duration=data.duration,
            poster=data.poster,
        )
        if not updated:
            raise MovieNotFoundError(movie_id)
        return updated

    def delete_movie(self, movie_id: int) -> bool:
        """Xóa phim theo ID. Ném MovieNotFoundError nếu phim không tồn tại."""
        deleted = self._repo.delete(movie_id)
        if not deleted:
            raise MovieNotFoundError(movie_id)
        return True

