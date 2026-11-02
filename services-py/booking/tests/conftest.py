"""Fixture dùng chung: MỌI test chạy trên SQLite tạm (tmp_path), không bao giờ đụng ./data/booking.db.

5 service đối tác được giả lập bằng httpx.MockTransport: code gọi HTTP của Booking vẫn chạy thật
(URL, query, header, JSON, giải mã envelope), chỉ không mở cổng mạng.
"""
import json
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_upstream
from app.core import clock, config
from app.db import init_schema, run_seed
from app.main import app
from app.services import UpstreamClient

PORTS = {5001: "movie", 5002: "showtime", 5003: "user", 5005: "payment", 5006: "notification"}
VALID_METHODS = {"BANK_TRANSFER", "MOMO", "VNPAY", "CASH"}


def _ok(data, status=200):
    return httpx.Response(status, json={"status": "success", "data": data})


def _err(status, code, message):
    return httpx.Response(status, json={"status": "error", "code": code, "message": message})


class FakeUpstreams:
    """Hành xử như 5 service Python thật theo API_CONTRACT (Payment trả id chuỗi, 409 ALREADY_PAID...)."""

    def __init__(self):
        future = clock.format_time(clock.now() + timedelta(days=1))
        past = clock.format_time(clock.now() - timedelta(hours=1))
        self.users = {"user1", "user2"}
        self.movies = {1, 2}
        self.showtimes = {
            1: {"id": 1, "movieId": 1, "cinema": "CGV", "room": "P1", "time": future, "price": 90000},
            2: {"id": 2, "movieId": 2, "cinema": "CGV", "room": "P2", "time": future, "price": 75000},
            3: {"id": 3, "movieId": 1, "cinema": "CGV", "room": "P3", "time": past, "price": 90000},
        }
        self.transactions: list[dict] = []
        self.calls: list[httpx.Request] = []
        self.down: set[str] = set()  # không kết nối được
        self.broken: set[str] = set()  # trả HTTP 500
        self.lose_payment_reply = False  # Payment đã ghi giao dịch nhưng phản hồi bị mất
        self.on_payment = None  # chạy ngay khi Payment nhận POST (giả lập việc xảy ra trong lúc chờ)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        service = PORTS[request.url.port]
        if service in self.down:
            raise httpx.ConnectError("connection refused", request=request)
        if service in self.broken:
            return _err(500, "INTERNAL_ERROR", "Lỗi máy chủ nội bộ")
        return getattr(self, f"_{service}")(request)

    def service_calls(self, service: str) -> list[httpx.Request]:
        return [r for r in self.calls if PORTS[r.url.port] == service]

    def _user(self, request):
        username = request.url.params.get("username")
        rows = [{"id": 2, "username": username, "email": None, "role": "USER"}] if username in self.users else []
        return _ok(rows)

    def _movie(self, request):
        movie_id = int(request.url.path.rsplit("/", 1)[1])
        if movie_id not in self.movies:
            return _err(404, "NOT_FOUND", "Không tìm thấy phim")
        return _ok({"id": movie_id, "title": "Phim"})

    def _showtime(self, request):
        showtime = self.showtimes.get(int(request.url.path.rsplit("/", 1)[1]))
        return _ok(showtime) if showtime else _err(404, "NOT_FOUND", "Không tìm thấy suất chiếu")

    def _payment(self, request):
        if request.method == "GET":
            booking_id = int(request.url.params["bookingId"])
            return _ok([t for t in reversed(self.transactions) if t["bookingId"] == booking_id])
        body = json.loads(request.content)
        if self.on_payment:
            self.on_payment(body)
        if any(t["bookingId"] == body["bookingId"] and t["status"] == "PAID" for t in self.transactions):
            return _err(409, "ALREADY_PAID", f"Đơn #{body['bookingId']} đã được thanh toán")
        paid = body["amount"] > 0 and body["method"] in VALID_METHODS
        transaction = {
            "id": str(len(self.transactions) + 1),
            "bookingId": body["bookingId"],
            "amount": body["amount"],
            "method": body["method"],
            "status": "PAID" if paid else "FAILED",
            "paidAt": "2026-11-02T10:00:00Z",
        }
        self.transactions.append(transaction)
        if self.lose_payment_reply:
            raise httpx.ReadTimeout("reply lost", request=request)
        return _ok(transaction, 201)

    def _notification(self, request):
        return _ok({"notificationId": 1, "deliveryStatus": "SIMULATED"})


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    path = tmp_path / "booking.db"
    monkeypatch.setattr(config, "DB_PATH", str(path))
    return path


@pytest.fixture
def upstreams():
    return FakeUpstreams()


@pytest.fixture
def client(upstreams):
    init_schema()
    stub = UpstreamClient(httpx.MockTransport(upstreams))
    app.dependency_overrides[get_upstream] = lambda: stub
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_client(client):
    run_seed()
    return client


@pytest.fixture
def order():
    """Body đặt vé hợp lệ; truyền tham số để đổi từng trường."""

    def build(**overrides):
        return {"username": "user1", "movieId": 1, "showtimeId": 1, "seats": ["A1", "A2"], **overrides}

    return build
