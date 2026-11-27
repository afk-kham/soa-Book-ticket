"""Kiểm thử end-to-end bằng pytest + httpx (theo mẫu Unit 22).

CHỈ chạy trên môi trường cô lập (DB tạm + cổng riêng qua SOA_PORT_OFFSET hoặc SOA_GATEWAY_URL),
vì bộ test này tạo tài khoản và đơn đặt vé thật. Tự động skip khi hệ thống chưa bật.
"""
import os
import time

import httpx
import pytest

HOST = os.environ.get("SOA_HOST") or os.environ.get("HOST", "localhost")
PORT_OFFSET = int(os.environ.get("SOA_PORT_OFFSET", "0"))
GATEWAY_URL = os.environ.get("SOA_GATEWAY_URL", "").strip().rstrip("/")
_BASE_PORTS = {
    "movie": 5001,
    "showtime": 5002,
    "user": 5003,
    "booking": 5004,
    "payment": 5005,
    "notification": 5006,
}


def _url(svc: str) -> str:
    return GATEWAY_URL if GATEWAY_URL else f"http://{HOST}:{_BASE_PORTS[svc] + PORT_OFFSET}"


@pytest.fixture(scope="module")
def http():
    with httpx.Client(timeout=10.0, trust_env=False) as client:
        try:
            probe = f"{GATEWAY_URL}/health" if GATEWAY_URL else f"{_url('booking')}/health"
            if client.get(probe).status_code != 200:
                pytest.skip("Hệ thống SOA chưa sẵn sàng để chạy test E2E")
        except httpx.RequestError:
            pytest.skip("Hệ thống SOA không phản hồi; bỏ qua test E2E")
        yield client


def _pick_showtime_and_seat(client: httpx.Client) -> tuple[dict, str]:
    shows = client.get(f"{_url('showtime')}/api/showtimes").json()["data"]
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    upcoming = next((s for s in shows if s["time"] > now_str), None)
    if upcoming is None:
        pytest.skip("Không có suất chiếu sắp tới")
    taken = set(
        client.get(f"{_url('booking')}/api/booking/seats", params={"showtimeId": upcoming["id"]}).json()["data"]["seats"]
    )
    for row in "ABCDEFGH":
        for col in range(1, 13):
            seat = f"{row}{col}"
            if seat not in taken:
                return upcoming, seat
    pytest.skip("Không còn ghế trống cho suất chiếu thử nghiệm")


def test_e2e_create_booking_success_has_notification_and_enrichment(http: httpx.Client):
    uname = f"e2e_{int(time.time() * 1000)}"
    reg = http.post(f"{_url('user')}/api/register", json={"username": uname, "password": "Test@123", "email": f"{uname}@x.vn"})
    assert reg.status_code == 201
    showtime, seat = _pick_showtime_and_seat(http)

    res = http.post(
        f"{_url('booking')}/api/booking",
        json={
            "username": uname,
            "movieId": showtime["movieId"],
            "showtimeId": showtime["id"],
            "seats": [seat],
            "paymentMethod": "MOMO",
            "payNow": True,
        },
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["status"] == "PAID"
    assert data["notification"] in ("SENT", "FAILED", "SKIPPED")
    assert data["unitPrice"] == showtime["price"]
    assert data["totalPrice"] == showtime["price"]


def test_e2e_movie_not_found_returns_404(http: httpx.Client):
    showtime, _ = _pick_showtime_and_seat(http)
    res = http.post(
        f"{_url('booking')}/api/booking",
        json={"username": "user1", "movieId": 999999, "showtimeId": showtime["id"], "seats": ["Z9"]},
    )
    assert res.status_code == 404
    assert res.json()["code"] == "MOVIE_NOT_FOUND"


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "user1", "movieId": 1, "showtimeId": 1, "seats": []},
        {"username": "user1", "movieId": 1, "showtimeId": 1, "seats": ["zz"]},
        {"username": "user1", "movieId": 0, "showtimeId": 1, "seats": ["Z8"]},
        {"username": "user1", "movieId": -1, "showtimeId": 1, "seats": ["Z8"]},
        {"username": "user1", "movieId": 1, "showtimeId": 0, "seats": ["Z8"]},
        {"username": "user1", "movieId": 1, "showtimeId": -1, "seats": ["Z8"]},
    ],
)
def test_e2e_invalid_booking_payload_returns_400(http: httpx.Client, payload: dict):
    res = http.post(f"{_url('booking')}/api/booking", json=payload)
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"
