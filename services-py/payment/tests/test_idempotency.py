"""Idempotency-Key: gửi lại cùng khóa không tạo giao dịch mới, không cần OTP mới; khác nội dung -> 409."""
import threading

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.db.init_db import init_db
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "payment.db"))
    monkeypatch.setattr(config, "OTP_REQUIRED", False)
    init_db(seed=False)
    return TestClient(app)


BODY = {"bookingId": 7, "amount": 90000, "method": "MOMO"}


def post(client, key, body=None, **extra):
    return client.post("/api/payment", json={**(body or BODY), **extra}, headers={"Idempotency-Key": key} if key else {})


def count(client, booking_id=7):
    return len(client.get(f"/api/payment?bookingId={booking_id}").json()["data"])


def test_same_key_replays_first_response_without_new_transaction(client):
    first = post(client, "pay-7-a")
    again = post(client, "pay-7-a")
    assert first.status_code == again.status_code == 201
    assert again.json() == first.json() and again.headers["idempotency-replayed"] == "true"
    assert "idempotency-replayed" not in first.headers
    assert count(client) == 1


def test_without_key_behaves_as_before(client):
    assert post(client, None).status_code == 201
    assert post(client, None).status_code == 409  # ALREADY_PAID như cũ


def test_same_key_different_body_is_409(client):
    post(client, "k1")
    r = post(client, "k1", {**BODY, "amount": 1})
    assert r.status_code == 409 and r.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert post(client, "k1", {**BODY, "method": "momo"}).status_code == 201  # chuẩn hóa chữ hoa: coi là cùng nội dung


def test_different_keys_for_paid_booking_hit_already_paid(client):
    post(client, "k1")
    r = post(client, "k2")
    assert r.status_code == 409 and r.json()["code"] == "ALREADY_PAID"
    assert count(client) == 1


def test_failed_attempts_are_not_cached_so_retry_works(client):
    r = post(client, "k1", {**BODY, "amount": 0})  # FAILED vẫn là 201 -> được lưu theo khóa
    assert r.status_code == 201 and r.json()["data"]["status"] == "FAILED"
    ok = post(client, "k2")  # khóa mới -> thử lại được
    assert ok.json()["data"]["status"] == "PAID"


def test_replay_does_not_need_a_new_otp(client, monkeypatch):
    monkeypatch.setattr(config, "OTP_REQUIRED", True)
    monkeypatch.setattr(config, "OTP_RESEND_SECONDS", 0)
    otp = client.post("/api/payment/otp", json={"bookingId": 7}).json()["data"]["otp"]
    first = post(client, "pay-otp", otp=otp)
    assert first.status_code == 201
    again = post(client, "pay-otp", otp=otp)  # OTP đã bị tiêu thụ nhưng replay vẫn trả kết quả cũ
    assert again.status_code == 201 and again.json() == first.json()
    assert post(client, "pay-other", otp=otp).json()["code"] == "OTP_INVALID"  # khóa khác thì OTP không dùng lại được


def test_error_responses_are_not_stored(client, monkeypatch):
    monkeypatch.setattr(config, "OTP_REQUIRED", True)
    monkeypatch.setattr(config, "OTP_RESEND_SECONDS", 0)
    assert post(client, "k1").json()["code"] == "OTP_REQUIRED"
    otp = client.post("/api/payment/otp", json={"bookingId": 7}).json()["data"]["otp"]
    assert post(client, "k1", otp=otp).status_code == 201  # cùng khóa nhưng lần trước lỗi nên chưa lưu


@pytest.mark.parametrize("key", ["", "a b", "x" * 65, "<script>", "a/b"])
def test_invalid_key_is_400(client, key):
    r = client.post("/api/payment", json=BODY, headers={"Idempotency-Key": key})
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"
    assert count(client) == 0


def test_concurrent_requests_with_same_key_create_one_transaction(client):
    results = []

    def go():
        results.append(post(client, "race").status_code)

    threads = [threading.Thread(target=go) for _ in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results == [201] * 6 and count(client) == 1


def test_cors_allows_idempotency_key_header(client):
    r = client.options("/api/payment", headers={"Origin": "http://x", "Access-Control-Request-Method": "POST"})
    assert "Idempotency-Key" in r.headers["access-control-allow-headers"]
