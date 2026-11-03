"""Test VNPAY Sandbox: chữ ký, tạo URL, nhận kết quả trả về. Dùng DB tạm, không gọi mạng."""
import hashlib
import hmac
from urllib.parse import parse_qsl, quote_plus, urlsplit

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.db.init_db import init_db
from app.main import app

SECRET = "TESTSECRET"


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
