"""Truy vết request: middleware X-Request-ID được đăng ký cho app thật và hoạt động đúng."""
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.request_id import RequestIdMiddleware, request_id_var
from app.main import app as real_app


def _mini():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware, service="mini")

    @app.get("/ping")
    def ping():
        return {"rid": request_id_var.get()}

    return TestClient(app)


def test_real_app_registers_request_id_middleware():
    assert any(m.cls is RequestIdMiddleware for m in real_app.user_middleware)


def test_generates_and_echoes_request_id():
    c = _mini()
    r = c.get("/ping")
    assert len(r.headers["x-request-id"]) == 16 and r.json()["rid"] == r.headers["x-request-id"]
    r = c.get("/ping", headers={"X-Request-ID": "gw-1.a_b"})
    assert r.headers["x-request-id"] == "gw-1.a_b" and r.json()["rid"] == "gw-1.a_b"


def test_unsafe_request_id_is_replaced():
    r = _mini().get("/ping", headers={"X-Request-ID": "a b<c>"})
    assert r.headers["x-request-id"] != "a b<c>" and len(r.headers["x-request-id"]) == 16


def test_access_log_has_rid_and_no_query_or_body(caplog):
    trace = logging.getLogger("trace")
    trace.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="trace"):
            _mini().get("/ping?otp=987654", headers={"X-Request-ID": "rid-9"})
    finally:
        trace.propagate = False
    lines = [r.getMessage() for r in caplog.records if r.name == "trace"]
    assert any("rid=rid-9" in m and "service=mini" in m and "GET /ping -> 200" in m for m in lines)
    assert not any("987654" in m for m in lines)
