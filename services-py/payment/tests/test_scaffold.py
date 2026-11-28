"""Test khung: chỉ kiểm tra app khởi động được và không tự tạo DB. KHÔNG phải test nghiệp vụ."""
from pathlib import Path

from fastapi.testclient import TestClient

from app.core import config
from app.main import app


def test_health_ok():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "success", "data": {"service": "payment-service", "port": 5005}}


def test_importing_app_does_not_create_database_file(tmp_path):
    import os
    import subprocess
    import sys

    db = tmp_path / "should_not_exist" / "payment.db"
    service_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "DB_PATH": str(db), "PYTHONPATH": str(service_root)}
    subprocess.run([sys.executable, "-c", "import app.main"], cwd=tmp_path, env=env, check=True)
    assert not db.exists() and not db.parent.exists()
    assert not (tmp_path / "data").exists()


def test_declared_libraries_are_installed():
    import importlib

    for module in ['jwt']:
        importlib.import_module(module)
