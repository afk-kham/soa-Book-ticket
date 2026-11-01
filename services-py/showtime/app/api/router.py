"""HTTP routes for the Showtime API."""
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app import controllers
from app.core import config

api_router = APIRouter()


@api_router.get("/health")
def health():
    return {"status": "success", "data": {"service": config.SERVICE_NAME, "port": config.PORT}}


@api_router.get("/api/showtimes")
async def list_showtimes(
    movie_id_camel: str | None = Query(default=None, alias="movieId"),
    movie_id_snake: str | None = Query(default=None, alias="movie_id"),
    upcoming: str | None = None,
):
    return await controllers.list_showtimes(
        movie_id_camel, movie_id_snake, upcoming
    )


@api_router.get("/api/showtimes/{showtime_id}")
def get_showtime(showtime_id: int):
    return controllers.get_showtime(showtime_id)


@api_router.post("/api/showtimes", status_code=201)
async def create_showtime(request: Request):
    return await controllers.create_showtime(request)


@api_router.put("/api/showtimes/{showtime_id}")
async def update_showtime(showtime_id: int, request: Request):
    return await controllers.update_showtime(showtime_id, request)


@api_router.delete("/api/showtimes/{showtime_id}")
def delete_showtime(showtime_id: int):
    return controllers.delete_showtime(showtime_id)


@api_router.options("/health")
@api_router.options("/api/showtimes")
def options_collection() -> Response:
    return Response(status_code=204)


@api_router.options("/api/showtimes/{showtime_id}")
def options_showtime(showtime_id: int) -> Response:
    _ = showtime_id
    return Response(status_code=204)
