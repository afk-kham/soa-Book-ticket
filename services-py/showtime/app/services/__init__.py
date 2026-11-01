"""Business rules for Showtime; no HTTP request or SQL access belongs here."""

import logging
import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.core import config
from app.entities import Showtime
from app.repositories import (
    create_showtime,
    delete_showtime,
    get_scheduled_days,
    get_showtime,
    list_movie_ids,
    list_showtimes,
    schedule_transaction,
    update_showtime,
)

logger = logging.getLogger("showtime-service")

_CINEMAS = (
    "CGV Vincom Đồng Khởi",
    "Lotte Cinema Cantavil",
    "BHD Star Bitexco",
)
_SCHEDULE_SLOTS = ("09:30", "12:15", "15:00", "17:45", "20:30", "22:45")


class ShowtimeServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _not_found(showtime_id: int) -> ShowtimeServiceError:
    return ShowtimeServiceError(
        404, "NOT_FOUND", f"Không tìm thấy suất chiếu với ID = {showtime_id}"
    )


async def _assert_movie_exists(movie_id: int) -> None:
    if not config.VALIDATE_MOVIE:
        return
    url = f"{config.MOVIE_SERVICE_URL.rstrip('/')}/api/movies/{movie_id}"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url)
    except httpx.RequestError as exc:
        logger.warning("Không gọi được Movie Service để kiểm tra movieId: %s", exc)
        raise ShowtimeServiceError(
            503,
            "MOVIE_SERVICE_UNAVAILABLE",
            "Không gọi được Movie Service để kiểm tra movieId",
        ) from exc

    if response.status_code == 404:
        raise ShowtimeServiceError(
            400,
            "MOVIE_NOT_FOUND",
            f"Không tồn tại phim có movieId = {movie_id}",
        )
    if response.status_code != 200:
        raise ShowtimeServiceError(
            503,
            "MOVIE_SERVICE_UNAVAILABLE",
            "Movie Service trả lỗi khi kiểm tra movieId",
        )


async def create(data: dict[str, object]) -> Showtime:
    await _assert_movie_exists(int(data["movie_id"]))
    return create_showtime(
        movie_id=int(data["movie_id"]),
        cinema=str(data["cinema"]),
        room=str(data["room"]),
        showtime=str(data["time"]),
        price=int(data["price"]),
    )


async def update(showtime_id: int, changes: dict[str, object]) -> Showtime:
    current = get_showtime(showtime_id)
    if current is None:
        raise _not_found(showtime_id)
    if "movie_id" in changes:
        await _assert_movie_exists(int(changes["movie_id"]))
    updated = update_showtime(showtime_id, changes)
    if updated is None:
        raise _not_found(showtime_id)
    return updated


def get(showtime_id: int) -> Showtime:
    showtime = get_showtime(showtime_id)
    if showtime is None:
        raise _not_found(showtime_id)
    return showtime


def remove(showtime_id: int) -> dict[str, int | bool]:
    if not delete_showtime(showtime_id):
        raise _not_found(showtime_id)
    return {"id": showtime_id, "deleted": True}


def _local_now() -> datetime:
    try:
        configured_timezone = ZoneInfo(config.APP_TIMEZONE)
    except ZoneInfoNotFoundError:
        if config.APP_TIMEZONE != "Asia/Ho_Chi_Minh":
            raise
        logger.warning(
            "Không tìm thấy timezone database; dùng UTC+07:00 cho Asia/Ho_Chi_Minh"
        )
        configured_timezone = timezone(timedelta(hours=7))
    return datetime.now(configured_timezone)


def _movie_ids_from_response(data: object) -> list[int]:
    if not isinstance(data, dict) or data.get("status") != "success":
        return []
    movies = data.get("data")
    if not isinstance(movies, list):
        return []
    movie_ids = {
        movie["id"]
        for movie in movies
        if isinstance(movie, dict)
        and isinstance(movie.get("id"), int)
        and not isinstance(movie.get("id"), bool)
        and movie["id"] > 0
    }
    return sorted(movie_ids)


async def _schedule_movie_ids() -> list[int]:
    url = f"{config.MOVIE_SERVICE_URL.rstrip('/')}/api/movies"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url)
        if response.status_code == 200:
            movie_ids = _movie_ids_from_response(response.json())
            if movie_ids:
                return movie_ids
        else:
            logger.warning(
                "Movie Service trả HTTP %s khi lấy danh sách phim",
                response.status_code,
            )
    except (httpx.RequestError, ValueError) as exc:
        logger.warning("Không lấy được danh sách phim để xếp lịch: %s", exc)
    return list_movie_ids()


def _schedule_rows(
    day: datetime, movie_ids: list[int]
) -> list[tuple[int, str, str, str, int]]:
    rows: list[tuple[int, str, str, str, int]] = []
    weekend = day.weekday() >= 5
    for movie_index, movie_id in enumerate(movie_ids):
        for cinema_index, cinema in enumerate(_CINEMAS):
            slot_indexes = (
                (movie_index + cinema_index) % len(_SCHEDULE_SLOTS),
                (movie_index + cinema_index + 3) % len(_SCHEDULE_SLOTS),
            )
            for slot_index in slot_indexes:
                slot = _SCHEDULE_SLOTS[slot_index]
                hour, minute = map(int, slot.split(":"))
                price = 75_000
                if hour < 12:
                    price -= 10_000
                if hour >= 17:
                    price += 10_000
                if weekend:
                    price += 15_000
                showtime = datetime.combine(day.date(), time(hour, minute))
                rows.append(
                    (
                        movie_id,
                        cinema,
                        f"P{movie_index % 8 + 1}",
                        showtime.strftime("%Y-%m-%d %H:%M:%S"),
                        price,
                    )
                )
    return rows


async def ensure_schedule() -> None:
    if config.AUTO_SCHEDULE_DAYS <= 0:
        return

    now = _local_now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=config.AUTO_SCHEDULE_DAYS)
    scheduled_days = get_scheduled_days(start, end)
    missing_days = [
        start + timedelta(days=offset)
        for offset in range(config.AUTO_SCHEDULE_DAYS)
        if (start + timedelta(days=offset)).strftime("%Y-%m-%d")
        not in scheduled_days
    ]
    if not missing_days:
        return

    movie_ids = await _schedule_movie_ids()
    if not movie_ids:
        return
    rows_by_day = {
        day.strftime("%Y-%m-%d"): _schedule_rows(day, movie_ids)
        for day in missing_days
    }
    with schedule_transaction() as transaction:
        scheduled_days = transaction.get_scheduled_days(start, end)
        rows = [
            row
            for day, day_rows in rows_by_day.items()
            if day not in scheduled_days
            for row in day_rows
        ]
        transaction.insert_showtimes(rows)


async def list_all(
    movie_id: int | None = None, upcoming: bool = False
) -> list[Showtime]:
    await ensure_schedule()
    upcoming_after = _local_now().strftime("%Y-%m-%d %H:%M:%S") if upcoming else None
    return list_showtimes(movie_id=movie_id, upcoming_after=upcoming_after)


def parse_movie_filter(value: str | None) -> int | None:
    if value is None:
        return None
    if re.fullmatch(r"-?\d+", value) is None or int(value) <= 0:
        raise ShowtimeServiceError(
            400, "VALIDATION_ERROR", "movieId phải là số nguyên dương"
        )
    return int(value)


def parse_upcoming(value: str | None) -> bool:
    return value is not None and value.lower() in {"1", "true"}
