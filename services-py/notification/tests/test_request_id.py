"""Truy vết request: X-Request-ID được nhận, sinh, trả lại và ghi log (không lộ nội dung)."""
import logging

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.db.init_db import init_schema
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    init_schema(seed=True)
    return TestClient(app)


def test_generates_request_id_when_missing(client):
    r = client.get("/health")
    rid = r.headers["x-request-id"]
    assert len(rid) == 16 and rid.isalnum()
    assert client.get("/health").headers["x-request-id"] != rid


def test_echoes_valid_incoming_request_id(client):
    r = client.get("/health", headers={"X-Request-ID": "gw-abc_123.4"})
    assert r.headers["x-request-id"] == "gw-abc_123.4"


@pytest.mark.parametrize("bad", ["a b", "x" * 65, "<script>", "a;b"])
def test_rejects_unsafe_request_id_and_generates_new(client, bad):
    r = client.get("/health", headers={"X-Request-ID": bad})
    assert r.headers["x-request-id"] != bad and len(r.headers["x-request-id"]) == 16


def test_error_responses_also_carry_request_id(client):
    r = client.get("/khong-co")
    assert r.status_code == 404 and r.headers["x-request-id"]


def test_access_log_has_id_and_no_secrets(client, caplog):
    with caplog.at_level(logging.INFO, logger="trace"):
        trace = logging.getLogger("trace")
        trace.propagate = True  # để caplog bắt được
        try:
            client.get("/api/notify/logs?username=nguoi_bi_mat", headers={"X-Request-ID": "rid-test-1"})
        finally:
            trace.propagate = False
    lines = [r.getMessage() for r in caplog.records if r.name == "trace"]
    assert any("rid=rid-test-1" in m and "service=notification-service" in m and "/api/notify/logs -> 200" in m for m in lines)
    assert not any("nguoi_bi_mat" in m for m in lines)  # query không được ghi vào log
