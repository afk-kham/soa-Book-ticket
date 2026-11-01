"""Test hành vi API Notification theo API_CONTRACT §7. Dùng DB SQLite tạm (tmp_path), không đụng dữ liệu thật."""
import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.db.init_db import init_schema
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    init_schema(seed=True)
    return TestClient(app)


def notify(client, **over):
    body = {"username": "user1", "bookingId": 5, "channel": "EMAIL", **over}
    return client.post("/api/notify", json=body)


def err(r, status, code):
    assert r.status_code == status, r.text
    j = r.json()
    assert j["status"] == "error" and j["code"] == code and j["message"]
    return j


# ---------- POST /api/notify ----------
def test_notify_ok_returns_200_and_writes_log(client):
    r = notify(client, username="  an  ", channel=" sms ")
    assert r.status_code == 200
    d = r.json()["data"]
    assert r.json()["status"] == "success"
    assert d["deliveryStatus"] == "SIMULATED" and d["username"] == "an" and d["channel"] == "SMS"
    assert d["message"] == "Đặt vé thành công cho đơn #5" and d["sentAt"].endswith("Z") and len(d["sentAt"]) == 20
    logs = client.get("/api/notify/logs?bookingId=5").json()["data"]
    assert len(logs) == 1 and logs[0]["id"] == d["notificationId"]


@pytest.mark.parametrize("body", [
    {"username": "u", "bookingId": 0, "channel": "EMAIL"},
    {"username": "u", "bookingId": -1, "channel": "EMAIL"},
    {"username": "u", "bookingId": 2147483648, "channel": "EMAIL"},
    {"username": "  ", "bookingId": 1, "channel": "EMAIL"},
    {"username": "ệ" * 51, "bookingId": 1, "channel": "EMAIL"},
    {"username": "u", "bookingId": 1, "channel": "PUSH"},
    {"username": "u", "bookingId": 1, "channel": "EMAIL", "message": "x"},  # trường lạ
    {"username": "u", "bookingId": 1.5, "channel": "EMAIL"},
    {"username": "u", "bookingId": "1", "channel": "EMAIL"},
    {"username": "u", "bookingId": True, "channel": "EMAIL"},
])
def test_notify_validation_400(client, body):
    err(client.post("/api/notify", json=body), 400, "VALIDATION_ERROR")


@pytest.mark.parametrize("raw", [b"", b"null", b"[]", b"{", b'{"a":1} {}', b'{"username":"\xff"}'])
def test_notify_bad_body_400(client, raw):
    err(client.post("/api/notify", content=raw, headers={"Content-Type": "application/json"}), 400, "VALIDATION_ERROR")


def test_notify_body_too_large_413(client):
    err(client.post("/api/notify", content=b" " * (16 * 1024 + 1)), 413, "PAYLOAD_TOO_LARGE")


def test_notify_failure_does_not_leak_details(client, monkeypatch):
    from app.controllers import notification_controller as c

    def boom(*a, **k):
        raise RuntimeError("SELECT secret FROM x")
    monkeypatch.setattr(c.service.repo, "insert", boom)
    j = err(notify(client), 500, "INTERNAL_ERROR")
    assert "secret" not in j["message"] and "SELECT" not in j["message"]


# ---------- GET /api/notify/logs ----------
def test_list_newest_first_and_filters(client):
    notify(client, bookingId=7, channel="SMS", username="Bob")
    notify(client, bookingId=8, channel="EMAIL", username="bob")
    data = client.get("/api/notify/logs").json()["data"]
    assert [x["id"] for x in data] == sorted((x["id"] for x in data), reverse=True)
    assert len(client.get("/api/notify/logs?username=BOB").json()["data"]) == 2
    assert len(client.get("/api/notify/logs?channel=sms").json()["data"]) == 1
    assert len(client.get("/api/notify/logs?bookingId=1").json()["data"]) == 1  # bản ghi seed
    assert client.get("/api/notify/logs?bookingId=999").json()["data"] == []


@pytest.mark.parametrize("q", ["bookingId=abc", "bookingId=0", "bookingId=-3", "channel=PUSH"])
def test_list_bad_filter_400(client, q):
    err(client.get("/api/notify/logs?" + q), 400, "VALIDATION_ERROR")


def test_root_lists_all_logs_same_as_logs_endpoint(client):
    notify(client, bookingId=30)
    r = client.get("/")
    assert r.status_code == 200 and r.json()["status"] == "success"
    assert r.json()["data"] == client.get("/api/notify/logs").json()["data"]
    assert len(r.json()["data"]) == 2  # seed + vừa tạo


# ---------- POST /api/notify/logs ----------
def test_create_log_201_default_message(client):
    r = client.post("/api/notify/logs", json={"username": "u", "bookingId": 9, "channel": "email"})
    assert r.status_code == 201
    d = r.json()["data"]
    assert d["message"] == "Đặt vé thành công cho đơn #9" and d["channel"] == "EMAIL" and d["bookingId"] == 9


def test_create_log_custom_message_and_limits(client):
    r = client.post("/api/notify/logs", json={"username": "u", "bookingId": 9, "channel": "SMS", "message": "x" * 255})
    assert r.status_code == 201
    err(client.post("/api/notify/logs", json={"username": "u", "bookingId": 9, "channel": "SMS", "message": "x" * 256}),
        400, "VALIDATION_ERROR")
    err(client.post("/api/notify/logs", json={"username": "u", "bookingId": 9, "channel": "SMS",
                                              "message": "a", "content": "b"}), 400, "VALIDATION_ERROR")


def test_create_log_with_recipient_validation(client):
    ok = {"recipient": "a@b.vn", "bookingId": 3, "channel": "EMAIL", "content": "Xin chào"}
    assert client.post("/api/notify/logs", json=ok).status_code == 201
    err(client.post("/api/notify/logs", json={**ok, "recipient": "khong-phai-email"}), 400, "VALIDATION_ERROR")
    err(client.post("/api/notify/logs", json={**ok, "channel": "SMS", "recipient": "123"}), 400, "VALIDATION_ERROR")
    assert client.post("/api/notify/logs", json={**ok, "channel": "SMS", "recipient": "+84901234567"}).status_code == 201
    err(client.post("/api/notify/logs", json={"recipient": "a@b.vn", "bookingId": 3, "channel": "EMAIL"}),
        400, "VALIDATION_ERROR")  # thiếu nội dung


# ---------- GET /api/notify/logs/{id} ----------
def test_get_log(client):
    d = client.get("/api/notify/logs/1").json()["data"]
    assert d == {"id": 1, "bookingId": 1, "username": "user1", "channel": "EMAIL",
                 "message": "Đặt vé thành công cho đơn #1", "sentAt": "2026-10-01T10:02:00Z"}
    err(client.get("/api/notify/logs/999"), 404, "NOT_FOUND")


@pytest.mark.parametrize("bad", ["abc", "0", "-1", "1.5"])
def test_get_log_bad_id_400(client, bad):
    err(client.get("/api/notify/logs/" + bad), 400, "VALIDATION_ERROR")


def test_unknown_paths_404(client):
    err(client.get("/missing"), 404, "NOT_FOUND")
    err(client.get("/api/notify/logs/1/extra"), 404, "NOT_FOUND")
    err(client.post("/api/notify/", json={}), 404, "NOT_FOUND")  # không chuyển hướng 307


# ---------- PUT|PATCH /api/notify/logs/{id} ----------
@pytest.mark.parametrize("method", ["put", "patch"])
def test_update_partial(client, method):
    r = getattr(client, method)("/api/notify/logs/1", json={"message": "  Nội dung mới  ", "bookingId": 77})
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["message"] == "Nội dung mới" and d["bookingId"] == 77 and d["username"] == "user1"
    assert d["sentAt"] == "2026-10-01T10:02:00Z"  # sentAt không đổi


def test_update_channel_and_username(client):
    d = client.put("/api/notify/logs/1", json={"channel": "sms", "username": " zed "}).json()["data"]
    assert d["channel"] == "SMS" and d["username"] == "zed"


def test_update_errors(client):
    err(client.put("/api/notify/logs/999", json={"message": "x"}), 404, "NOT_FOUND")
    err(client.put("/api/notify/logs/999", json={"bookingId": 3}), 404, "NOT_FOUND")
    err(client.put("/api/notify/logs/1", json={"channel": "PUSH"}), 400, "VALIDATION_ERROR")
    err(client.put("/api/notify/logs/1", json={"username": " "}), 400, "VALIDATION_ERROR")
    err(client.put("/api/notify/logs/1", json={"message": ""}), 400, "VALIDATION_ERROR")
    err(client.put("/api/notify/logs/1", json={"message": "x" * 256}), 400, "VALIDATION_ERROR")
    err(client.put("/api/notify/logs/1", json={"bookingId": 0}), 400, "VALIDATION_ERROR")
    err(client.put("/api/notify/logs/1", json={"sentAt": "2020-01-01T00:00:00Z"}), 400, "VALIDATION_ERROR")
    err(client.put("/api/notify/logs/abc", json={}), 400, "VALIDATION_ERROR")
    assert client.put("/api/notify/logs/1", json={}).status_code == 200  # không có gì để sửa


# ---------- DELETE ----------
def test_delete(client):
    r = client.delete("/api/notify/logs/1")
    assert r.status_code == 200
    assert r.json()["data"] == {"id": 1, "deleted": True, "message": "Đã xóa nhật ký thông báo thành công"}
    err(client.get("/api/notify/logs/1"), 404, "NOT_FOUND")
    err(client.delete("/api/notify/logs/1"), 404, "NOT_FOUND")
    new_id = notify(client).json()["data"]["notificationId"]
    assert new_id > 1  # id đã xóa không bị cấp lại


# ---------- CORS / 405 ----------
def test_options_204_with_cors(client):
    r = client.options("/api/notify", headers={"Origin": "http://localhost:8081", "Access-Control-Request-Method": "POST"})
    assert r.status_code == 204 and r.content == b""
    assert r.headers["access-control-allow-origin"] == "*"
    assert "DELETE" in r.headers["access-control-allow-methods"]
    assert client.options("/api/notify/logs/1").status_code == 204


def test_method_not_allowed_has_envelope_allow_and_cors(client):
    r = client.get("/api/notify")
    err(r, 405, "METHOD_NOT_ALLOWED")
    assert "POST" in r.headers["allow"]
    assert r.headers["access-control-allow-origin"] == "*"
    err(client.post("/api/notify/logs/1", json={}), 405, "METHOD_NOT_ALLOWED")


def test_error_responses_carry_cors(client):
    assert client.get("/missing").headers["access-control-allow-origin"] == "*"
