import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

import jwt
import pytest
import httpx
from fastapi.testclient import TestClient
from fastapi import Query

from app.core import config
from app.db.init_db import init_db
from app.db.connection import get_connection
from app.main import app
from app.core.jwt_auth import JwtAuthError, verify_authorization_header, verify_jwt


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "payment.db"))
    init_db(seed=False)
    return TestClient(app)


def test_post_paid_for_all_valid_methods(client):
    for index, method in enumerate(("BANK_TRANSFER", "momo", "VnPay", "cash"), start=1):
        response = client.post(
            "/api/payment",
            json={"bookingId": 10 + index, "amount": 90000, "method": method},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status"] == "PAID"
        assert data["method"] == method.strip().upper()


def test_post_failed_non_positive_amount_is_saved(client):
    for amount in (0, -1):
        response = client.post(
            "/api/payment",
            json={"bookingId": 100 + amount, "amount": amount, "method": "MOMO"},
        )
        assert response.status_code == 201
        assert response.json()["data"]["status"] == "FAILED"


def test_post_failed_unknown_method_is_saved(client):
    response = client.post(
        "/api/payment",
        json={"bookingId": 200, "amount": 90000, "method": "BANK"},
    )
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "FAILED"
    assert response.json()["data"]["method"] == "BANK"


def test_paid_booking_rejected_on_second_post(client):
    payload = {"bookingId": 300, "amount": 90000, "method": "CASH"}
    assert client.post("/api/payment", json=payload).status_code == 201
    response = client.post("/api/payment", json=payload)
    assert response.status_code == 409
    assert response.json()["status"] == "error"
    assert response.json()["code"] == "ALREADY_PAID"


def test_failed_payment_allows_retry(client):
    first = client.post(
        "/api/payment",
        json={"bookingId": 301, "amount": 0, "method": "MOMO"},
    )
    second = client.post(
        "/api/payment",
        json={"bookingId": 301, "amount": 90000, "method": "MOMO"},
    )
    assert first.status_code == 201
    assert first.json()["data"]["status"] == "FAILED"
    assert second.status_code == 201
    assert second.json()["data"]["status"] == "PAID"


@pytest.mark.parametrize(
    "booking_id",
    [
        0,
        -1,
        True,
        False,
        1.5,
        90000.0,
        "3",
        None,
        9223372036854775808,
    ],
)
def test_invalid_booking_id(client, booking_id):
    response = client.post(
        "/api/payment",
        json={"bookingId": booking_id, "amount": 90000, "method": "MOMO"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "amount",
    [
        "90000",
        90000.5,
        90000.0,
        None,
        True,
        False,
        -9223372036854775809,
        9223372036854775808,
    ],
)
def test_invalid_amount(client, amount):
    response = client.post(
        "/api/payment",
        json={"bookingId": 400, "amount": amount, "method": "MOMO"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("method", ["", "   ", 123])
def test_invalid_method(client, method):
    response = client.post(
        "/api/payment",
        json={"bookingId": 401, "amount": 90000, "method": method},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("body", [None, "{", "[]"])
def test_empty_malformed_or_non_object_body(client, body):
    if body is None:
        response = client.post("/api/payment")
    else:
        response = client.post(
            "/api/payment",
            content=body,
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 400
    assert response.json()["status"] == "error"
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_body_over_one_mib(client):
    response = client.post(
        "/api/payment",
        content=b"x" * (1024 * 1024 + 1),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "PAYLOAD_TOO_LARGE"
    assert "SQL" not in str(response.json())
    assert "Traceback" not in str(response.json())


def test_body_over_one_mib_without_content_length(client):
    async def send_chunked():
        async def chunks():
            yield b"x"
            yield b"x" * (1024 * 1024)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            follow_redirects=False,
        ) as async_client:
            return await async_client.post(
                "/api/payment",
                content=chunks(),
                headers={
                    "Content-Type": "application/json",
                    "Transfer-Encoding": "chunked",
                },
            )

    response = asyncio.run(send_chunked())
    assert response.status_code == 413
    assert response.json()["code"] == "PAYLOAD_TOO_LARGE"


def test_body_at_one_mib_boundary_with_content_length(client):
    body = b"{}" + b" " * (1024 * 1024 - 2)
    response = client.post(
        "/api/payment",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_get_sorted_filters_and_response_shape(client):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO transactions (id,booking_id,amount,method,status,paid_at) VALUES (?, ?, ?, ?, ?, ?)",
            (501, 501, 90000, "MOMO", "PAID", "2026-01-01T10:00:00Z"),
        )
        conn.execute(
            "INSERT INTO transactions (id,booking_id,amount,method,status,paid_at) VALUES (?, ?, ?, ?, ?, ?)",
            (502, 502, 90000, "CASH", "PAID", "2026-01-02T10:00:00Z"),
        )
        conn.commit()

    response = client.get("/api/payment")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data[0]["id"] == "502"
    assert data[1]["id"] == "501"

    filtered = client.get("/api/payment?bookingId=501")
    assert filtered.status_code == 200
    assert len(filtered.json()["data"]) == 1
    assert filtered.json()["data"][0]["bookingId"] == 501

    assert isinstance(data[0]["id"], str)
    assert data[0]["paidAt"].endswith("Z")


@pytest.mark.parametrize("booking_id", ["abc", "0", "-1", "1.0", "999999999999999999999"])
def test_invalid_booking_filter(client, booking_id):
    response = client.get("/api/payment", params={"bookingId": booking_id})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_options_returns_204(client):
    response = client.options("/api/payment")
    assert response.status_code == 204
    assert response.headers["access-control-allow-origin"] == "*"


@pytest.mark.parametrize("path", ["/docs", "/docs/", "/redoc", "/redoc/", "/openapi.json"])
def test_documentation_routes_are_disabled(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json() == {
        "status": "error",
        "code": "NOT_FOUND",
        "message": "Không tìm thấy endpoint",
    }


def test_method_not_allowed_uses_error_envelope(client):
    response = client.put("/api/payment", json={"bookingId": 1})
    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"
    assert "Traceback" not in str(response.json())
    assert "SQL" not in str(response.json())


def test_not_found_uses_error_envelope(client):
    response = client.get("/api/not-found")
    assert response.status_code == 404
    assert response.json()["status"] == "error"
    assert response.json()["code"] == "NOT_FOUND"
    assert response.json()["message"] == "Không tìm thấy endpoint"


def test_validation_status_422_is_converted_to_error_envelope(client):
    @app.get("/__validation_test")
    def validation_test(value: int = Query(gt=0)):
        return {"value": value}

    try:
        response = client.get("/__validation_test?value=-1")
        assert response.status_code == 400
        assert response.json() == {
            "status": "error",
            "code": "VALIDATION_ERROR",
            "message": "Dữ liệu yêu cầu không hợp lệ",
        }
    finally:
        app.router.routes.pop()


def test_unexpected_error_uses_internal_error_envelope(client):
    @app.get("/__unexpected_test")
    def unexpected_test():
        raise RuntimeError("sqlite secret traceback")

    try:
        response = client.get("/__unexpected_test")
        assert response.status_code == 500
        assert response.json()["status"] == "error"
        assert response.json()["code"] == "INTERNAL_ERROR"
        assert "sqlite" not in str(response.json()).lower()
        assert "traceback" not in str(response.json()).lower()
    finally:
        app.router.routes.pop()


def test_init_db_seed_then_get_returns_two_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "payment.db"))
    init_db(seed=True)
    init_db(seed=True)

    with get_connection() as conn:
        seed_rows = conn.execute(
            "SELECT id, booking_id, amount, method, status "
            "FROM transactions WHERE id IN (1, 2) ORDER BY id"
        ).fetchall()
        assert len(seed_rows) == 2
        assert [row["id"] for row in seed_rows] == [1, 2]

    seed_client = TestClient(app)
    response = seed_client.get("/api/payment")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 2
    assert [item["id"] for item in data] == ["2", "1"]

    new_response = seed_client.post(
        "/api/payment",
        json={"bookingId": 3, "amount": 90000, "method": "MOMO"},
    )
    assert new_response.status_code == 201
    assert new_response.json()["data"]["id"] == "3"


def test_more_than_twelve_ids_are_unique_increasing_and_strings(client):
    created_ids = []
    for booking_id in range(700, 715):
        response = client.post(
            "/api/payment",
            json={"bookingId": booking_id, "amount": 90000, "method": "MOMO"},
        )
        assert response.status_code == 201
        payment_id = response.json()["data"]["id"]
        assert isinstance(payment_id, str)
        created_ids.append(int(payment_id))

    assert len(created_ids) == len(set(created_ids))
    assert created_ids == sorted(created_ids)
    assert max(created_ids) >= 12

    response = client.get("/api/payment")
    listed_ids = [int(item["id"]) for item in response.json()["data"]]
    assert len(listed_ids) >= 15
    assert all(isinstance(item["id"], str) for item in response.json()["data"])


def test_concurrent_paid_requests_allow_one_and_reject_other(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "payment.db"))
    init_db(seed=False)
    payload = {"bookingId": 800, "amount": 90000, "method": "MOMO"}

    def post_payment():
        with TestClient(app) as concurrent_client:
            return concurrent_client.post("/api/payment", json=payload)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: post_payment(), range(2)))

    statuses = sorted(response.status_code for response in responses)
    assert statuses == [201, 409]


def make_token(secret, **overrides):
    now = int(time.time())
    claims = {
        "sub": "user1",
        "userId": 1,
        "role": "USER",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return jwt.encode(claims, secret, algorithm="HS256")


def test_jwt_valid(monkeypatch):
    secret = "a" * 32
    monkeypatch.setattr(config, "JWT_SECRET", secret)
    token = make_token(secret, iat=int(time.time()) + 30)
    claims = verify_jwt(token)
    assert claims["role"] == "USER"


def test_jwt_expired_singular(monkeypatch):
    secret = "a" * 32
    monkeypatch.setattr(config, "JWT_SECRET", secret)
    token = make_token(secret, exp=int(time.time()) - 120)
    with pytest.raises(JwtAuthError) as exc:
        verify_jwt(token)
    assert exc.value.status_code == 401


def test_jwt_wrong_signature(monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "a" * 32)
    token = make_token("b" * 32)
    with pytest.raises(JwtAuthError) as exc:
        verify_jwt(token)
    assert exc.value.status_code == 401


def test_jwt_missing_and_forbidden(monkeypatch):
    secret = "a" * 32
    monkeypatch.setattr(config, "JWT_SECRET", secret)
    with pytest.raises(JwtAuthError) as exc:
        verify_authorization_header(None)
    assert exc.value.status_code == 401

    token = make_token(secret, role="USER")
    with pytest.raises(JwtAuthError) as exc:
        verify_authorization_header(f"Bearer {token}", required_role="ADMIN")
    assert exc.value.status_code == 403
