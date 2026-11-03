"""Test VNPAY Sandbox: chữ ký, tạo URL, nhận kết quả trả về. Dùng DB tạm, không gọi mạng."""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, quote_plus, urlsplit

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.db.init_db import init_db
from app.main import app

SECRET = "TESTSECRET"
VN = timezone(timedelta(hours=7))
VNP_TIME = "%Y%m%d%H%M%S"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "payment.db"))
    monkeypatch.setattr(config, "VNPAY_TMN_CODE", "TMN1")
    monkeypatch.setattr(config, "VNPAY_HASH_SECRET", SECRET)
    monkeypatch.setattr(config, "CLIENT_URL", "http://client.test")
    init_db(seed=False)
    return TestClient(app, follow_redirects=False)


def _signed(params: dict) -> dict:
    q = "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted(params.items()))
    return {**params, "vnp_SecureHash": hmac.new(SECRET.encode(), q.encode(), hashlib.sha512).hexdigest()}


def _return(client, **over):
    p = {"vnp_TxnRef": "7_1700000000", "vnp_Amount": "9000000", "vnp_ResponseCode": "00",
         "vnp_TransactionStatus": "00", "vnp_OrderInfo": "Thanh toan ve"}
    return client.get("/api/payment/vnpay/return", params=_signed({**p, **over}))


def test_create_returns_signed_url(client):
    r = client.post("/api/payment/vnpay/create", json={"bookingId": 7, "amount": 90000})
    assert r.status_code == 201
    d = r.json()["data"]
    assert d["txnRef"].startswith("7_")
    parts = urlsplit(d["paymentUrl"])
    assert parts.netloc == "sandbox.vnpayment.vn"
    q = dict(parse_qsl(parts.query))
    assert q["vnp_Amount"] == "9000000" and q["vnp_TmnCode"] == "TMN1" and q["vnp_TxnRef"] == d["txnRef"]
    from app.services import vnpay
    assert vnpay.verify_signature(q)


@pytest.mark.parametrize("body", [{"bookingId": 0, "amount": 1}, {"bookingId": 1, "amount": 0},
                                  {"bookingId": 1, "amount": "9"}, {"amount": 5}])
def test_create_validation_400(client, body):
    assert client.post("/api/payment/vnpay/create", json=body).status_code == 400


def _create_query(client, expires_at) -> dict:
    r = client.post("/api/payment/vnpay/create", json={"bookingId": 7, "amount": 90000, "expiresAt": expires_at})
    assert r.status_code == 201, r.text
    return dict(parse_qsl(urlsplit(r.json()["data"]["paymentUrl"]).query))


def test_create_without_expires_keeps_15_minutes(client):
    q = _create_query(client, None)
    created, expire = (datetime.strptime(q[k], VNP_TIME) for k in ("vnp_CreateDate", "vnp_ExpireDate"))
    assert expire - created == timedelta(minutes=15)


def test_create_expiry_capped_one_minute_before_hold(client):
    # Đúng định dạng expiresAt Booking trả: giờ Việt Nam, không kèm múi giờ
    hold = (datetime.now(VN) + timedelta(minutes=5)).replace(microsecond=0)
    q = _create_query(client, hold.strftime("%Y-%m-%d %H:%M:%S"))
    assert q["vnp_ExpireDate"] == (hold - timedelta(minutes=1)).strftime(VNP_TIME)


def test_create_expiry_accepts_iso_with_offset(client):
    hold = (datetime.now(timezone.utc) + timedelta(minutes=5)).replace(microsecond=0)
    q = _create_query(client, hold.strftime("%Y-%m-%dT%H:%M:%SZ"))
    assert q["vnp_ExpireDate"] == (hold.astimezone(VN) - timedelta(minutes=1)).strftime(VNP_TIME)


def test_create_long_hold_still_15_minutes(client):
    q = _create_query(client, (datetime.now(VN) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"))
    created, expire = (datetime.strptime(q[k], VNP_TIME) for k in ("vnp_CreateDate", "vnp_ExpireDate"))
    assert expire - created == timedelta(minutes=15)


@pytest.mark.parametrize("left", [timedelta(seconds=30), timedelta(minutes=-3)])
def test_create_hold_almost_over_409(client, left):
    hold = (datetime.now(VN) + left).strftime("%Y-%m-%d %H:%M:%S")
    r = client.post("/api/payment/vnpay/create", json={"bookingId": 7, "amount": 90000, "expiresAt": hold})
    assert r.status_code == 409 and r.json()["code"] == "HOLD_EXPIRED"


@pytest.mark.parametrize("value", ["ngay mai", "", 1700000000])
def test_create_bad_expires_400(client, value):
    r = client.post("/api/payment/vnpay/create", json={"bookingId": 7, "amount": 90000, "expiresAt": value})
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


def test_create_not_configured_503(client, monkeypatch):
    monkeypatch.setattr(config, "VNPAY_HASH_SECRET", "")
    r = client.post("/api/payment/vnpay/create", json={"bookingId": 1, "amount": 1000})
    assert r.status_code == 503 and r.json()["code"] == "VNPAY_NOT_CONFIGURED"


def test_return_success_records_paid_and_redirects(client):
    r = _return(client)
    assert r.status_code == 302 and r.headers["location"] == "http://client.test/#/vnpay-return/7/ok"
    tx = client.get("/api/payment?bookingId=7").json()["data"]
    assert len(tx) == 1 and tx[0]["status"] == "PAID" and tx[0]["method"] == "VNPAY" and tx[0]["amount"] == 90000
    assert _return(client).headers["location"].endswith("/7/ok")  # tải lại: không tạo thêm, vẫn thành công
    assert len(client.get("/api/payment?bookingId=7").json()["data"]) == 1


def test_return_failed_code_records_nothing(client):
    r = _return(client, vnp_ResponseCode="24", vnp_TransactionStatus="02")
    assert r.headers["location"].endswith("/7/fail")
    assert client.get("/api/payment?bookingId=7").json()["data"] == []


def test_return_bad_signature_records_nothing(client):
    p = _signed({"vnp_TxnRef": "7_1", "vnp_Amount": "9000000", "vnp_ResponseCode": "00"})
    p["vnp_Amount"] = "100"  # bị sửa sau khi ký
    r = client.get("/api/payment/vnpay/return", params=p)
    assert r.status_code == 302 and r.headers["location"] == "http://client.test/#/my"
    assert client.get("/api/payment").json()["data"] == []


def test_return_garbage_redirects_home(client):
    assert client.get("/api/payment/vnpay/return").headers["location"] == "http://client.test/#/my"
