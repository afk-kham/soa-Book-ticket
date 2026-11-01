"""Test khung: app khởi động được, /health đúng dạng và import app không tự tạo DB."""
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "success", "data": {"service": "notification-service", "port": 5006}}


def test_importing_app_does_not_create_database_file(tmp_path):
    # Tiến trình con + DB_PATH tạm: không phụ thuộc file ./data/notification.db có thể đã có trên máy dev.
    db = tmp_path / "sub" / "x.db"
    env = {**os.environ, "DB_PATH": str(db)}
    subprocess.run([sys.executable, "-c", "import app.main"], check=True, env=env,
                   cwd=Path(__file__).resolve().parents[1])
    assert not db.exists() and not db.parent.exists()


def test_declared_libraries_are_installed():
    import importlib

    for module in ['jwt']:
        importlib.import_module(module)
