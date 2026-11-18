"""OTP xác nhận thanh toán: sinh, kiểm tra, hết hạn, khóa khi nhập sai, dùng một lần, gửi lại."""
import time

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.db.init_db import init_db
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "payment.db"))
    monkeypatch.setattr(config, "OTP_REQUIRED", True)
    monkeypatch.setattr(config, "OTP_RESEND_SECONDS", 0)
    init_db(seed=False)
    return TestClient(app)


def otp_for(client, booking_id=7):
    r = client.post("/api/payment/otp", json={"bookingId": booking_id})
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    assert d["bookingId"] == booking_id and len(d["otp"]) == 6 and d["otp"].isdigit() and d["ttlSeconds"] == 300
    return d["otp"]


def pay(client, otp=None, booking_id=7):
    body = {"bookingId": booking_id, "amount": 90000, "method": "MOMO"}
    if otp is not None:
        body["otp"] = otp
    return client.post("/api/payment", json=body)


def code(r):
    return r.json().get("code")


def test_payment_without_otp_is_rejected_when_required(client):
    r = pay(client)
    assert r.status_code == 400 and code(r) == "OTP_REQUIRED"
    assert client.get("/api/payment?bookingId=7").json()["data"] == []


def test_payment_with_correct_otp_succeeds_and_otp_is_single_use(client):
    otp = otp_for(client)
    r = pay(client, otp)
    assert r.status_code == 201 and r.json()["data"]["status"] == "PAID"
    again = pay(client, otp)  # mã đã dùng
    assert again.status_code == 400 and code(again) == "OTP_INVALID"


def test_wrong_otp_rejected_and_nothing_recorded(client):
    otp_for(client)
    r = pay(client, "000000" if otp_for(client) != "000000" else "111111")
    assert r.status_code == 400 and code(r) == "OTP_INVALID"
    assert client.get("/api/payment?bookingId=7").json()["data"] == []


def test_otp_is_bound_to_its_booking(client):
    otp = otp_for(client, 7)
    r = pay(client, otp, booking_id=8)
    assert r.status_code == 400 and code(r) == "OTP_INVALID"


def test_otp_expires(client, monkeypatch):
    otp = otp_for(client)
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + config.OTP_TTL_SECONDS + 1)
    r = pay(client, otp)
    assert r.status_code == 400 and code(r) == "OTP_EXPIRED"


def test_locked_after_too_many_wrong_attempts_even_with_right_code(client):
    otp = otp_for(client)
    wrong = "123456" if otp != "123456" else "654321"
    for _ in range(config.OTP_MAX_ATTEMPTS - 1):
        assert code(pay(client, wrong)) == "OTP_INVALID"
    last = pay(client, wrong)
    assert last.status_code == 429 and code(last) == "OTP_LOCKED"
    locked = pay(client, otp)  # mã đúng cũng bị từ chối
    assert locked.status_code == 429 and code(locked) == "OTP_LOCKED"
    new = otp_for(client)  # yêu cầu mã mới thì mở khóa
    assert pay(client, new).status_code == 201


def test_resend_too_soon_429(client, monkeypatch):
    monkeypatch.setattr(config, "OTP_RESEND_SECONDS", 60)
    otp_for(client)
    r = client.post("/api/payment/otp", json={"bookingId": 7})
    assert r.status_code == 429 and code(r) == "OTP_TOO_SOON"
    assert client.post("/api/payment/otp", json={"bookingId": 8}).status_code == 201  # đơn khác không bị ảnh hưởng


def test_new_otp_replaces_old(client):
    first = otp_for(client)
    second = otp_for(client)
    if first != second:  # (xác suất trùng 1e-6)
        assert code(pay(client, first)) == "OTP_INVALID"
    assert pay(client, second).status_code == 201


def test_otp_optional_but_validated_when_not_required(client, monkeypatch):
    monkeypatch.setattr(config, "OTP_REQUIRED", False)
    assert pay(client).status_code == 201  # tương thích ngược: không gửi otp
    r = pay(client, "999999", booking_id=9)  # có gửi thì phải đúng
    assert r.status_code == 400 and code(r) == "OTP_INVALID"


def test_otp_hash_is_stored_not_plaintext(client):
    import sqlite3

    otp = otp_for(client)
    row = sqlite3.connect(config.DB_PATH).execute("SELECT salt, code_hash FROM otp_challenges").fetchone()
    assert otp not in row[0] + row[1] and len(row[1]) == 64


@pytest.mark.parametrize("body", [{}, {"bookingId": 0}, {"bookingId": "7"}, {"bookingId": -1}])
def test_otp_create_validation_400(client, body):
    assert client.post("/api/payment/otp", json=body).status_code == 400


def test_vnpay_return_is_not_blocked_by_otp(client, monkeypatch):
    """VNPAY tự xác thực người trả tiền nên luồng return không đòi OTP."""
    from app.services import create_payment

    assert create_payment(7, 90000, "VNPAY").status == "PAID"
