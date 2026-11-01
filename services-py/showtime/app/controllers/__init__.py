"""HTTP-facing request parsing and response-envelope handling."""

import json

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app import services
from app.entities import Showtime
from app.schemas import ShowtimeCreate, ShowtimeResponse, ShowtimeUpdate
from app.services import ShowtimeServiceError


def _success(data: object, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"status": "success", "data": data},
    )


def _error(
    status_code: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"status": "error", "code": code, "message": message},
        headers=headers,
    )


def _service_error(error: ShowtimeServiceError) -> JSONResponse:
    return _error(error.status_code, error.code, error.message)


def _validation_message(error: ValidationError) -> str:
    field = str(error.errors()[0]["loc"][0]) if error.errors() else ""
    messages = {
        "movieId": "movieId phải là số nguyên dương",
        "movie_id": "movieId phải là số nguyên dương",
        "cinema": "cinema là bắt buộc và tối đa 150 ký tự",
        "room": "room là bắt buộc và tối đa 50 ký tự",
        "time": "time phải có dạng YYYY-MM-DD HH:MM[:SS]",
        "price": "price phải là số nguyên không âm (VND)",
    }
    return messages.get(field, "Dữ liệu suất chiếu không hợp lệ")


async def _read_json_object(request: Request) -> dict[str, object] | JSONResponse:
    raw_body = await request.body()
    if not raw_body.strip():
        return _error(400, "VALIDATION_ERROR", "Body yêu cầu rỗng")
    try:
        body = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error(400, "VALIDATION_ERROR", "Body phải là một đối tượng JSON hợp lệ")
    if not isinstance(body, dict):
        return _error(400, "VALIDATION_ERROR", "Body phải là một đối tượng JSON hợp lệ")
    return body


def _showtime_data(showtime: Showtime) -> dict[str, object]:
    return ShowtimeResponse(
        id=showtime.id,
        movie_id=showtime.movie_id,
        cinema=showtime.cinema,
        room=showtime.room,
        time=showtime.time,
        price=showtime.price,
    ).model_dump(by_alias=True)


async def list_showtimes(
    movie_id_camel: str | None,
    movie_id_snake: str | None,
    upcoming: str | None,
) -> JSONResponse:
    try:
        movie_id = services.parse_movie_filter(
            movie_id_camel if movie_id_camel is not None else movie_id_snake
        )
        showtimes = await services.list_all(
            movie_id=movie_id, upcoming=services.parse_upcoming(upcoming)
        )
        return _success([_showtime_data(showtime) for showtime in showtimes])
    except ShowtimeServiceError as error:
        return _service_error(error)


def get_showtime(showtime_id: int) -> JSONResponse:
    try:
        return _success(_showtime_data(services.get(showtime_id)))
    except ShowtimeServiceError as error:
        return _service_error(error)


async def create_showtime(request: Request) -> JSONResponse:
    body = await _read_json_object(request)
    if isinstance(body, JSONResponse):
        return body
    try:
        data = ShowtimeCreate.model_validate(body).model_dump()
    except ValidationError as error:
        return _error(400, "VALIDATION_ERROR", _validation_message(error))
    try:
        showtime = await services.create(data)
        return _success(_showtime_data(showtime), status_code=201)
    except ShowtimeServiceError as error:
        return _service_error(error)


async def update_showtime(showtime_id: int, request: Request) -> JSONResponse:
    try:
        services.get(showtime_id)
    except ShowtimeServiceError as error:
        return _service_error(error)

    body = await _read_json_object(request)
    if isinstance(body, JSONResponse):
        return body
    try:
        changes = ShowtimeUpdate.model_validate(body).changes()
    except ValidationError as error:
        return _error(400, "VALIDATION_ERROR", _validation_message(error))
    try:
        showtime = await services.update(showtime_id, changes)
        return _success(_showtime_data(showtime))
    except ShowtimeServiceError as error:
        return _service_error(error)


def delete_showtime(showtime_id: int) -> JSONResponse:
    try:
        return _success(services.remove(showtime_id))
    except ShowtimeServiceError as error:
        return _service_error(error)
