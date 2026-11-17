"""POST /api/login phát JWT HS256 thật khi có JWT_SECRET; không có thì giữ token demo."""
import time

import jwt
import pytest

from app.core import config

SECRET = "x" * 40


def login(client, username="user1", password="User@123"):
    r = client.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_demo_token_when_secret_not_configured(seeded_client, monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "")
    assert login(seeded_client)["token"] == "demo-token-user1"


def test_demo_token_when_secret_too_short(seeded_client, monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "ngan")
    assert login(seeded_client)["token"] == "demo-token-user1"


def test_real_jwt_with_required_claims(seeded_client, monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", SECRET)
    data = login(seeded_client)
    claims = jwt.decode(data["token"], SECRET, algorithms=["HS256"])
    assert claims["sub"] == "user1" and claims["role"] == "USER" and claims["userId"] == data["id"]
    assert claims["exp"] - claims["iat"] == 2 * 60 * 60
    assert abs(claims["iat"] - time.time()) < 10
    assert set(data) == {"id", "username", "role", "token"}


def test_admin_token_carries_admin_role(seeded_client, monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", SECRET)
    token = login(seeded_client, "admin", "Admin@123")["token"]
    assert jwt.decode(token, SECRET, algorithms=["HS256"])["role"] == "ADMIN"


def test_token_is_rejected_with_another_secret(seeded_client, monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", SECRET)
    token = login(seeded_client)["token"]
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "y" * 40, algorithms=["HS256"])


def test_wrong_password_never_issues_token(seeded_client, monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", SECRET)
    r = seeded_client.post("/api/login", json={"username": "user1", "password": "sai"})
    assert r.status_code == 401 and "token" not in r.text


def test_token_not_leaked_by_other_endpoints(seeded_client, monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", SECRET)
    login(seeded_client)
    assert "token" not in seeded_client.get("/api/users").text and SECRET not in seeded_client.get("/api/users").text
