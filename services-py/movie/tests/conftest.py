"""Fixture dùng chung: Mọi test chạy trên SQLite tạm (tmp_path), không đụng vào ./data/movie.db."""
import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.db import init_schema, run_seed
from app.main import app


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Tạo CSDL SQLite tạm thời cho từng ca test."""
    temp_db = tmp_path / "test_movie.db"
    monkeypatch.setattr(config, "DB_PATH", str(temp_db))
    return temp_db


@pytest.fixture
def client(isolated_db):
    """TestClient đã khởi tạo schema rỗng (chưa có dữ liệu phim)."""
    init_schema()
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def seeded_client(client):
    """TestClient đã có sẵn 5 bộ phim mẫu từ seed."""
    run_seed()
    return client

