"""Email thật qua SMTP (mock, không gửi mạng) và endpoint gửi OTP. Mã OTP không bao giờ được lưu vào nhật ký."""
import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.db.init_db import init_schema
from app.main import app
from app.services import sender as sender_mod


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "SMTP_HOST", "")
    init_schema(seed=True)
    return TestClient(app)


class FakeSMTP:
    sent: list = []
    fail: Exception | bool = False

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self, context=None):
        self.tls = True

    def login(self, user, password):
        self.creds = (user, password)

    def send_message(self, msg):
        if FakeSMTP.fail:
            if isinstance(FakeSMTP.fail, BaseException):
                raise FakeSMTP.fail
            raise OSError("smtp down")
        FakeSMTP.sent.append(msg)


@pytest.fixture()
def smtp(monkeypatch):
    FakeSMTP.sent, FakeSMTP.fail = [], False
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(config, "SMTP_USER", "bot@test")
    monkeypatch.setattr(config, "SMTP_PASSWORD", "pw")
    monkeypatch.setattr(config, "SMTP_FROM", "SOA Cinema <bot@test>")
    monkeypatch.setattr(sender_mod.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def otp_body(**over):
    return {"username": "user1", "bookingId": 5, "email": "user1@cinema.local", "otp": "123456", **over}


def test_otp_simulated_when_smtp_not_configured(client):
    r = client.post("/api/notify/otp", json=otp_body())
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["deliveryStatus"] == "SIMULATED" and d["channel"] == "EMAIL" and d["bookingId"] == 5
    assert "123456" not in r.text  # mã không lộ trong phản hồi


def test_otp_sent_by_real_email_when_smtp_configured(client, smtp):
    r = client.post("/api/notify/otp", json=otp_body())
    assert r.status_code == 200 and r.json()["data"]["deliveryStatus"] == "SENT"
    assert len(smtp.sent) == 1
    mail = smtp.sent[0]
    assert mail["To"] == "user1@cinema.local" and "OTP" in mail["Subject"] and "#5" in mail["Subject"]
    plain_part = mail.get_body(preferencelist=("plain",))
    html_part = mail.get_body(preferencelist=("html",))
    assert plain_part is not None and "1 2 3 4 5 6" in plain_part.get_content()
    assert html_part is not None and "font-size:32px" in html_part.get_content() and "1 2 3 4 5 6" in html_part.get_content()


def test_otp_never_stored_in_logs(client, smtp):
    client.post("/api/notify/otp", json=otp_body())
    logs = client.get("/api/notify/logs?bookingId=5").json()["data"]
    assert logs and all("123456" not in x["message"] for x in logs)
    assert "OTP" in logs[0]["message"]


def test_smtp_connection_failure_returns_503_without_details(client, smtp):
    smtp.fail = True
    r = client.post("/api/notify/otp", json=otp_body())
    assert r.status_code == 503 and r.json()["code"] == "EMAIL_PROVIDER_UNAVAILABLE"
    assert "smtp down" not in r.text


@pytest.mark.parametrize("exc, expected_status, expected_code, secret_detail", [
    (TimeoutError("timed out smtp.internal:587"), 503, "EMAIL_PROVIDER_UNAVAILABLE", "smtp.internal"),
    (ConnectionError("connection refused 10.0.0.5"), 503, "EMAIL_PROVIDER_UNAVAILABLE", "10.0.0.5"),
    (OSError("network unreachable"), 503, "EMAIL_PROVIDER_UNAVAILABLE", "network unreachable"),
    (__import__("smtplib").SMTPAuthenticationError(535, b"bad password secret123"), 502, "EMAIL_PROVIDER_ERROR", "secret123"),
    (__import__("smtplib").SMTPException("smtp internal error"), 502, "EMAIL_PROVIDER_ERROR", "smtp internal error"),
    (__import__("smtplib").SMTPRecipientsRefused({"u@bad.local": (550, b"no such user")}), 400, "EMAIL_REJECTED", "no such user"),
    (__import__("smtplib").SMTPSenderRefused(550, b"sender blocked", "bot@test"), 400, "EMAIL_REJECTED", "sender blocked"),
])
def test_smtp_error_mapping(client, smtp, exc, expected_status, expected_code, secret_detail):
    smtp.fail = exc
    r = client.post("/api/notify/otp", json=otp_body())
    assert r.status_code == expected_status
    assert r.json()["code"] == expected_code
    assert secret_detail not in r.text


def test_notify_endpoint_maps_smtp_unavailable_to_503(client, smtp):
    smtp.fail = TimeoutError("smtp timeout")
    r = client.post("/api/notify", json={"username": "user1", "bookingId": 5, "channel": "EMAIL", "email": "a@b.vn"})
    assert r.status_code == 503 and r.json()["code"] == "EMAIL_PROVIDER_UNAVAILABLE"


@pytest.mark.parametrize("over", [
    {"email": ""}, {"email": "khong-phai-email"}, {"otp": ""}, {"otp": "12"}, {"otp": "abcdef"}, {"otp": "123456789"},
    {"username": " "}, {"bookingId": 0}, {"ttlSeconds": 5}, {"ttlSeconds": 99999},
])
def test_otp_validation_400(client, over):
    r = client.post("/api/notify/otp", json=otp_body(**over))
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


def test_otp_unknown_field_rejected(client):
    assert client.post("/api/notify/otp", json=otp_body(extra=1)).status_code == 400


def test_confirmation_email_sent_when_email_given(client, smtp):
    r = client.post("/api/notify", json={"username": "user1", "bookingId": 5, "channel": "EMAIL", "email": "a@b.vn"})
    assert r.status_code == 200 and r.json()["data"]["deliveryStatus"] == "SENT"
    assert smtp.sent[0]["To"] == "a@b.vn" and "Xác nhận" in smtp.sent[0]["Subject"]


def test_confirmation_without_email_stays_simulated(client, smtp):
    a = client.post("/api/notify", json={"username": "u", "bookingId": 5, "channel": "EMAIL"})
    assert a.status_code == 200 and a.json()["data"]["deliveryStatus"] == "SIMULATED"
    assert smtp.sent == []


def test_confirmation_bad_email_400(client):
    r = client.post("/api/notify", json={"username": "u", "bookingId": 5, "channel": "EMAIL", "email": "xx"})
    assert r.status_code == 400


def test_starttls_and_login_used(client, smtp, monkeypatch):
    seen = {}
    real_init = FakeSMTP.__init__

    def spy(self, *a, **k):
        real_init(self, *a, **k)
        seen["inst"] = self

    monkeypatch.setattr(FakeSMTP, "__init__", spy)
    client.post("/api/notify/otp", json=otp_body())
    assert seen["inst"].tls is True and seen["inst"].creds == ("bot@test", "pw")
