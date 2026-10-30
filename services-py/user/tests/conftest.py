"""Fixture dùng chung: MỌI test chạy trên SQLite tạm (tmp_path), không bao giờ đụng ./data/user.db."""
import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.db import init_schema, run_seed
from app.main import app


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    path = tmp_path / "user.db"
    monkeypatch.setattr(config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(isolated_db):
    init_schema()
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def seeded_client(client):
    run_seed()
    return client


VALID = {"username": "alice_01", "password": "Secret1", "email": "alice@example.com"}


@pytest.fixture
def valid_user():
    return dict(VALID)
