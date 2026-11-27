import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app import services
from app.core import config
from app.db import connection
from app.main import app
from app.repositories import create_showtime, list_showtimes


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(connection, "DB_PATH", str(tmp_path / "showtime.db"))
    monkeypatch.setattr(config, "VALIDATE_MOVIE", False)
    monkeypatch.setattr(config, "AUTO_SCHEDULE_DAYS", 0)
    with TestClient(app) as test_client:
        yield test_client


def valid_payload():
    return {
        "movieId": 2,
        "cinema": "CGV",
        "room": "P1",
        "time": "2030-01-02T09:30",
        "price": 75000,
    }


def test_create_reads_legacy_movie_id_and_returns_camel_case(client):
    payload = valid_payload()
    payload["movie_id"] = payload.pop("movieId")

    response = client.post("/api/showtimes", json=payload)

    assert response.status_code == 201
    assert response.json() == {
        "status": "success",
        "data": {
            "id": 1,
            "movieId": 2,
            "cinema": "CGV",
            "room": "P1",
            "time": "2030-01-02 09:30:00",
            "price": 75000,
        },
    }


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"cinema": "C" * 151},
        {"room": "R" * 51},
        {"price": -1},
        {"movieId": 0},
        {"time": "2030-13-02 09:30"},
    ],
)
def test_create_validates_fields_and_does_not_call_movie_for_invalid_payload(
    client, invalid_fields
):
    response = client.post(
        "/api/showtimes", json={**valid_payload(), **invalid_fields}
    )

    assert response.status_code == 400
    assert response.json()["status"] == "error"
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert list_showtimes() == []


@pytest.mark.parametrize(
    ("movie_status", "expected_status", "expected_code"),
    [(404, 400, "MOVIE_NOT_FOUND"), (500, 502, "MOVIE_SERVICE_ERROR"), (502, 502, "MOVIE_SERVICE_ERROR")],
)
def test_movie_errors_are_mapped_to_contract(
    client, monkeypatch, movie_status, expected_status, expected_code
):
    real_async_client = httpx.AsyncClient
    requested_timeouts = []

    def async_client_factory(*, timeout):
        requested_timeouts.append(timeout)
        transport = httpx.MockTransport(
            lambda request: httpx.Response(movie_status, request=request)
        )
        return real_async_client(transport=transport, timeout=timeout)

    monkeypatch.setattr(config, "VALIDATE_MOVIE", True)
    monkeypatch.setattr(services.httpx, "AsyncClient", async_client_factory)

    response = client.post("/api/showtimes", json=valid_payload())

    assert response.status_code == expected_status
    assert response.json()["code"] == expected_code
    assert requested_timeouts == [3.0]
    assert list_showtimes() == []


def test_movie_lookup_unit19_four_cases(client, monkeypatch):
    """Bảng 4 tình huống Unit 19 cho Showtime -> Movie: 200->201, 404->400, RequestError->503, 500/HTML->502."""
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(config, "VALIDATE_MOVIE", True)

    def with_handler(handler):
        monkeypatch.setattr(
            services.httpx,
            "AsyncClient",
            lambda *, timeout: real_async_client(transport=httpx.MockTransport(handler), timeout=timeout),
        )

    # 1. Phim tồn tại (200) -> 201
    with_handler(lambda req: httpx.Response(200, json={"status": "success", "data": {"id": 2}}, request=req))
    r_ok = client.post("/api/showtimes", json=valid_payload())
    assert r_ok.status_code == 201

    # 2. Phim không tồn tại (404) -> 400 MOVIE_NOT_FOUND
    with_handler(lambda req: httpx.Response(404, json={"status": "error", "code": "NOT_FOUND"}, request=req))
    r_404 = client.post("/api/showtimes", json=valid_payload())
    assert r_404.status_code == 400 and r_404.json()["code"] == "MOVIE_NOT_FOUND"

    # 3. Mất kết nối / timeout (RequestError) -> 503 MOVIE_SERVICE_UNAVAILABLE
    def raise_connect(req):
        raise httpx.ConnectError("down", request=req)

    with_handler(raise_connect)
    r_down = client.post("/api/showtimes", json=valid_payload())
    assert r_down.status_code == 503 and r_down.json()["code"] == "MOVIE_SERVICE_UNAVAILABLE"

    # 4. Phản hồi bất thường (500 với JSON hỏng / HTML) -> 502 MOVIE_SERVICE_ERROR
    with_handler(lambda req: httpx.Response(500, text="<html>broken{json", request=req))
    r_bad = client.post("/api/showtimes", json=valid_payload())
    assert r_bad.status_code == 502 and r_bad.json()["code"] == "MOVIE_SERVICE_ERROR"


def test_update_checks_missing_id_before_invalid_body(client):
    response = client.put("/api/showtimes/99", content="{")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_update_delete_and_read_single_showtime(client):
    created = client.post("/api/showtimes", json=valid_payload()).json()["data"]

    updated = client.put(
        f"/api/showtimes/{created['id']}", json={"price": 0}
    )
    fetched = client.get(f"/api/showtimes/{created['id']}")
    deleted = client.delete(f"/api/showtimes/{created['id']}")

    assert updated.status_code == 200
    assert updated.json()["data"]["price"] == 0
    assert fetched.status_code == 200
    assert fetched.json()["data"]["movieId"] == 2
    assert deleted.json()["data"] == {"id": created["id"], "deleted": True}
    assert client.get(f"/api/showtimes/{created['id']}").status_code == 404


def test_list_filters_and_sorts_by_time_then_id(client):
    for showtime, movie_id in (
        ("2030-01-03 09:30:00", 3),
        ("2030-01-02 09:30:00", 2),
        ("2030-01-02 09:30:00", 2),
    ):
        client.post(
            "/api/showtimes",
            json={**valid_payload(), "movieId": movie_id, "time": showtime},
        )

    response = client.get("/api/showtimes?movie_id=2")

    assert response.status_code == 200
    data = response.json()["data"]
    assert [row["time"] for row in data] == [
        "2030-01-02 09:30:00",
        "2030-01-02 09:30:00",
    ]
    assert [row["id"] for row in data] == sorted(row["id"] for row in data)
    assert client.get("/api/showtimes?movieId=0").json()["code"] == "VALIDATION_ERROR"


def test_auto_schedule_fills_only_missing_days_once(client, monkeypatch):
    today = datetime(2030, 1, 5, tzinfo=timezone(timedelta(hours=7)))
    monkeypatch.setattr(config, "AUTO_SCHEDULE_DAYS", 2)
    monkeypatch.setattr(services, "_local_now", lambda: today)
    monkeypatch.setattr(services, "_schedule_movie_ids", lambda: async_ids([7]))
    create_showtime(99, "Manual", "R1", "2030-01-05 10:00:00", 50)

    async def concurrent_schedule_requests():
        await asyncio.gather(
            services.ensure_schedule(),
            services.ensure_schedule(),
        )

    asyncio.run(concurrent_schedule_requests())

    rows = list_showtimes()
    assert len(rows) == 7
    assert sum(row.time.startswith("2030-01-05") for row in rows) == 1
    assert sum(row.time.startswith("2030-01-06") for row in rows) == 6
    assert {row.price for row in rows if row.time.startswith("2030-01-06")} == {
        80_000,
        90_000,
        100_000,
    }


async def async_ids(movie_ids):
    return movie_ids


def test_options_is_no_content_and_errors_are_enveloped(client):
    preflight = client.options(
        "/api/showtimes",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    missing = client.get("/no-such-route")
    method_not_allowed = client.put("/api/showtimes")

    assert preflight.status_code == 204
    assert missing.status_code == 404
    assert missing.json() == {
        "status": "error",
        "code": "NOT_FOUND",
        "message": "Endpoint không tồn tại",
    }
    assert method_not_allowed.status_code == 405
    assert method_not_allowed.json()["code"] == "METHOD_NOT_ALLOWED"
    assert "Allow" in method_not_allowed.headers


@pytest.mark.parametrize("bad_value", ["", "   ", "abc", "0", "-1.5"])
def test_upstream_timeout_falls_back_to_default_on_invalid_env(monkeypatch, bad_value):
    monkeypatch.setenv("UPSTREAM_TIMEOUT_SECONDS", bad_value)
    assert config._positive_float("UPSTREAM_TIMEOUT_SECONDS", 3.0) == 3.0


def test_upstream_timeout_reads_valid_env(monkeypatch):
    monkeypatch.setenv("UPSTREAM_TIMEOUT_SECONDS", "4.5")
    assert config._positive_float("UPSTREAM_TIMEOUT_SECONDS", 3.0) == 4.5


def test_showtime_propagates_x_request_id_to_movie_on_create_and_auto_schedule(client, monkeypatch):
    from app import services as showtime_service

    monkeypatch.setattr(config, "VALIDATE_MOVIE", True)
    monkeypatch.setattr(config, "AUTO_SCHEDULE_DAYS", 1)
    seen_headers: list[tuple[str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append((request.url.path, request.headers.get("x-request-id")))
        if request.url.path == "/api/movies/1":
            return httpx.Response(200, json={"status": "success", "data": {"id": 1}})
        if request.url.path == "/api/movies":
            return httpx.Response(200, json={"status": "success", "data": [{"id": 1}]})
        return httpx.Response(404, json={"status": "error"})

    transport = httpx.MockTransport(handler)
    real_async_client = showtime_service.httpx.AsyncClient
    monkeypatch.setattr(
        showtime_service.httpx,
        "AsyncClient",
        lambda *args, **kwargs: real_async_client(transport=transport, **kwargs),
    )

    r1 = client.post(
        "/api/showtimes",
        json={"movieId": 1, "cinema": "CGV", "room": "P1", "time": "2030-01-01 18:00:00", "price": 90000},
        headers={"X-Request-ID": "trace-create-123"},
    )
    assert r1.status_code == 201
    r2 = client.get("/api/showtimes", headers={"X-Request-ID": "trace-list-456"})
    assert r2.status_code == 200
    assert ("/api/movies/1", "trace-create-123") in seen_headers
    assert ("/api/movies", "trace-list-456") in seen_headers


def test_showtime_omits_x_request_id_when_no_context(monkeypatch):
    import asyncio
    from app import services as showtime_service
    from app.core.request_id import request_id_var

    seen_headers: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(dict(request.headers))
        return httpx.Response(200, json={"status": "success", "data": {"id": 1}})

    transport = httpx.MockTransport(handler)
    real_async_client = showtime_service.httpx.AsyncClient
    monkeypatch.setattr(
        showtime_service.httpx,
        "AsyncClient",
        lambda *args, **kwargs: real_async_client(transport=transport, **kwargs),
    )
    token = request_id_var.set("-")
    try:
        asyncio.run(showtime_service._assert_movie_exists(1))
    finally:
        request_id_var.reset(token)
    assert seen_headers and "x-request-id" not in seen_headers[0]
