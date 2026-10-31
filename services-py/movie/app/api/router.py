"""Router của Movie Service: Khai báo path, method và chuyển giao cho Controller.

Tuân thủ đầy đủ API_CONTRACT.md:
  - GET  /health
  - GET  /api/movies
  - GET  /api/movies/{id}
  - POST /api/movies (201 Created)
  - PUT  /api/movies/{id} (200 OK)
  - DELETE /api/movies/{id} (200 OK)
"""
from fastapi import APIRouter, Depends, Path
from starlette.responses import Response

from app.api.deps import get_movie_controller
from app.controllers.movie_controller import MovieController
from app.core import config
from app.schemas.movie import MovieCreate, MovieUpdate

api_router = APIRouter()


@api_router.get(
    "/health",
    tags=["Health"],
    summary="Kiểm tra trạng thái dịch vụ (Health Check)",
    description="Trả về thông tin trạng thái hoạt động và cổng lắng nghe của Movie Service.",
)
def health():
    return {"status": "success", "data": {"service": config.SERVICE_NAME, "port": config.PORT}}


@api_router.get(
    "/api/movies",
    tags=["Movies"],
    summary="Lấy danh sách tất cả các phim",
    description="Trả về danh sách toàn bộ các bộ phim trong CSDL sắp xếp theo ID tăng dần (chuẩn camelCase).",
)
def list_movies(controller: MovieController = Depends(get_movie_controller)):
    return controller.list_movies()


@api_router.get(
    "/api/movies/{movie_id}",
    tags=["Movies"],
    summary="Lấy chi tiết một bộ phim theo ID",
    description="Tra cứu thông tin chi tiết của một bộ phim theo ID. Trả về 404 NOT_FOUND nếu không tìm thấy.",
)
def get_movie(
    movie_id: str = Path(..., description="ID số nguyên dương của bộ phim cần tra cứu", examples=["1"]),
    controller: MovieController = Depends(get_movie_controller),
):
    return controller.get_movie(movie_id)


@api_router.post(
    "/api/movies",
    status_code=201,
    tags=["Movies"],
    summary="Thêm phim mới",
    description="Tạo mới một bộ phim trong danh mục. Yêu cầu bắt buộc trường 'title' và 'duration > 0' nếu có.",
)
def create_movie(
    body: MovieCreate,
    controller: MovieController = Depends(get_movie_controller),
):
    return controller.create_movie(body)


@api_router.put(
    "/api/movies/{movie_id}",
    tags=["Movies"],
    summary="Cập nhật thông tin phim",
    description="Cập nhật một hoặc nhiều thông tin của phim theo ID. Trả về 404 nếu không tìm thấy phim.",
)
def update_movie(
    movie_id: str = Path(..., description="ID số nguyên dương của bộ phim cần cập nhật", examples=["1"]),
    body: MovieUpdate = ...,
    controller: MovieController = Depends(get_movie_controller),
):
    return controller.update_movie(movie_id, body)


@api_router.delete(
    "/api/movies/{movie_id}",
    tags=["Movies"],
    summary="Xóa phim theo ID",
    description="Xóa một bộ phim khỏi CSDL theo ID. Trả về 404 nếu phim không tồn tại.",
)
def delete_movie(
    movie_id: str = Path(..., description="ID số nguyên dương của bộ phim cần xóa", examples=["1"]),
    controller: MovieController = Depends(get_movie_controller),
):
    return controller.delete_movie(movie_id)


@api_router.options("/health", include_in_schema=False)
@api_router.options("/api/movies", include_in_schema=False)
@api_router.options("/api/movies/{movie_id}", include_in_schema=False)
def options_preflight(movie_id: str | None = None) -> Response:
    """Trả về HTTP 204 No Content cho các request OPTIONS preflight."""
    _ = movie_id
    return Response(status_code=204)
