"""Controller của Movie Service: Nhận request, gọi Service và đóng gói EnvelopeResponse chuẩn."""
import re
from app.core.http import EnvelopeResponse, error, success
from app.schemas.movie import MovieCreate, MovieResponse, MovieUpdate
from app.services.errors import MovieNotFoundError
from app.services.movie_service import MovieService

_ID_RE = re.compile(r"^[0-9]+$")


class MovieController:
    def __init__(self, service: MovieService):
        self._service = service

    def list_movies(self) -> EnvelopeResponse:
        """Lấy danh sách tất cả các bộ phim (HTTP 200)."""
        movies = self._service.list_movies()
        data = [MovieResponse.from_entity(m).to_dict() for m in movies]
        return success(200, data)

    def get_movie(self, raw_id: str) -> EnvelopeResponse:
        """Lấy chi tiết một bộ phim theo ID (HTTP 200 hoặc 404)."""
        if not _ID_RE.fullmatch(str(raw_id).strip()):
            return error(400, "ID phim phải là số nguyên dương", code="VALIDATION_ERROR")
        movie_id = int(raw_id)
        if movie_id <= 0:
            return error(400, "ID phim phải là số nguyên dương", code="VALIDATION_ERROR")
        try:
            movie = self._service.get_movie(movie_id)
            return success(200, MovieResponse.from_entity(movie).to_dict())
        except MovieNotFoundError:
            return error(404, f"Không tìm thấy phim với ID = {movie_id}", code="NOT_FOUND")

    def create_movie(self, body: MovieCreate) -> EnvelopeResponse:
        """Thêm phim mới (HTTP 201)."""
        movie = self._service.create_movie(body)
        return success(201, MovieResponse.from_entity(movie).to_dict())

    def update_movie(self, raw_id: str, body: MovieUpdate) -> EnvelopeResponse:
        """Cập nhật phim theo ID (HTTP 200 hoặc 404)."""
        if not _ID_RE.fullmatch(str(raw_id).strip()):
            return error(400, "ID phim phải là số nguyên dương", code="VALIDATION_ERROR")
        movie_id = int(raw_id)
        if movie_id <= 0:
            return error(400, "ID phim phải là số nguyên dương", code="VALIDATION_ERROR")
        try:
            movie = self._service.update_movie(movie_id, body)
            return success(200, MovieResponse.from_entity(movie).to_dict())
        except MovieNotFoundError:
            return error(404, f"Không tìm thấy phim với ID = {movie_id}", code="NOT_FOUND")

    def delete_movie(self, raw_id: str) -> EnvelopeResponse:
        """Xóa phim theo ID (HTTP 200 hoặc 404)."""
        if not _ID_RE.fullmatch(str(raw_id).strip()):
            return error(400, "ID phim phải là số nguyên dương", code="VALIDATION_ERROR")
        movie_id = int(raw_id)
        if movie_id <= 0:
            return error(400, "ID phim phải là số nguyên dương", code="VALIDATION_ERROR")
        try:
            self._service.delete_movie(movie_id)
            return success(200, {"id": movie_id, "deleted": True})
        except MovieNotFoundError:
            return error(404, f"Không tìm thấy phim với ID = {movie_id} để xóa", code="NOT_FOUND")

