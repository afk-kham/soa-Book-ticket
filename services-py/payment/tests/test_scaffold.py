"""Test khung: chỉ kiểm tra app khởi động được và không tự tạo DB. KHÔNG phải test nghiệp vụ."""
from pathlib import Path

from fastapi.testclient import TestClient

from app.core import config
from app.main import app


def test_health_ok():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "success", "data": {"service": "payment-service", "port": 5005}}


def test_importing_app_does_not_create_database_file():
    assert not Path(config.DB_PATH).exists()


def test_declared_libraries_are_installed():
    import importlib

    for module in ['jwt']:
        importlib.import_module(module)
