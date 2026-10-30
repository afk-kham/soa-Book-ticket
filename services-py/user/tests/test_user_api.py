"""Test nghiệp vụ User Service (DB tạm). Đối chiếu API_CONTRACT §4 và code Java cũ."""
import re
import sqlite3

import bcrypt
import pytest

from app.core import config
from app.repositories import UserRepository
from app.services import UserService


def err(r, status, code):
    assert r.status_code == status, r.text
    body = r.json()
    assert body["status"] == "error" and body["code"] == code
    assert isinstance(body["message"], str) and body["message"]
    assert set(body) == {"status", "code", "message"}
    return body["message"]


def no_secret(r):
    t = r.text.lower()
    assert "password" not in t and "hash" not in t and "$2a$" not in t and "$2b$" not in t


def db_rows():
    with sqlite3.connect(config.DB_PATH) as c:
        return c.execute("SELECT id, username, password_hash, email, role FROM users ORDER BY id").fetchall()


# ------------------------------------------------------------------ health / http
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "success", "data": {"service": "user-service", "port": 5003}}


def test_options_returns_204_with_cors(client):
    r = client.options("/api/login", headers={"Origin": "http://localhost:8080", "Access-Control-Request-Method": "POST"})
    assert r.status_code == 204 and r.content == b""
    assert r.headers["access-control-allow-origin"] == "*"
    assert "Authorization" in r.headers["access-control-allow-headers"]


def test_cors_header_on_success_and_error(client):
    assert client.get("/api/users").headers["access-control-allow-origin"] == "*"
    assert client.get("/api/users/abc").headers["access-control-allow-origin"] == "*"


def test_unknown_path_404_envelope(client):
    err(client.get("/api/nope"), 404, "NOT_FOUND")


def test_wrong_method_405_envelope(client):
    r = client.get("/api/login")
    err(r, 405, "METHOD_NOT_ALLOWED")
    assert "POST" in r.headers["allow"]
    err(client.delete("/api/users/1"), 405, "METHOD_NOT_ALLOWED")
    err(client.put("/api/users/1", json={}), 405, "METHOD_NOT_ALLOWED")
    err(client.post("/api/users", json={}), 405, "METHOD_NOT_ALLOWED")


def test_content_type_is_json_utf8(client):
    assert client.get("/api/users").headers["content-type"] == "application/json; charset=utf-8"


# ------------------------------------------------------------------ register
def test_register_ok(client, valid_user):
    r = client.post("/api/register", json=valid_user)
    assert r.status_code == 201
    assert r.json() == {"status": "success", "data": {"id": 1, "username": "alice_01", "email": "alice@example.com", "role": "USER"}}
    no_secret(r)


def test_register_without_email(client):
    r = client.post("/api/register", json={"username": "bob.x", "password": "abcdef"})
    assert r.status_code == 201 and r.json()["data"]["email"] is None


@pytest.mark.parametrize("email", ["", "   ", None])
def test_register_blank_email_becomes_null(client, email):
    r = client.post("/api/register", json={"username": "bob.x", "password": "abcdef", "email": email})
    assert r.status_code == 201 and r.json()["data"]["email"] is None


def test_register_ignores_client_role(client, valid_user):
    r = client.post("/api/register", json={**valid_user, "role": "ADMIN", "id": 99})
    assert r.status_code == 201
    assert r.json()["data"]["role"] == "USER" and r.json()["data"]["id"] == 1
    assert db_rows()[0][4] == "USER"


def test_register_trims_username(client):
    r = client.post("/api/register", json={"username": "  carol  ", "password": "abcdef"})
    assert r.status_code == 201 and r.json()["data"]["username"] == "carol"


def test_register_password_stored_as_bcrypt(client, valid_user):
    client.post("/api/register", json=valid_user)
    h = db_rows()[0][2]
    assert h != valid_user["password"] and valid_user["password"] not in h
    assert re.fullmatch(r"\$2a\$10\$.{53}", h)
    assert bcrypt.checkpw(valid_user["password"].encode(), h.encode())


def test_register_same_password_gives_different_hash(client):
    client.post("/api/register", json={"username": "u_one", "password": "samepass"})
    client.post("/api/register", json={"username": "u_two", "password": "samepass"})
    rows = db_rows()
    assert rows[0][2] != rows[1][2]


@pytest.mark.parametrize("body", [
    {}, {"password": "abcdef"}, {"username": None, "password": "abcdef"},
    {"username": 12345, "password": "abcdef"}, {"username": ["a", "b", "c"], "password": "abcdef"},
    {"username": "ab", "password": "abcdef"}, {"username": "a" * 51, "password": "abcdef"},
    {"username": "has space", "password": "abcdef"}, {"username": "dấu_tiếng_việt", "password": "abcdef"},
    {"username": "a-b-c", "password": "abcdef"}, {"username": "a@b.c", "password": "abcdef"},
    {"username": "a\nbc", "password": "abcdef"}, {"username": "   ", "password": "abcdef"},
    {"username": "abc'; DROP TABLE users;--", "password": "abcdef"},
])
def test_register_invalid_username(client, body):
    msg = err(client.post("/api/register", json=body), 400, "VALIDATION_ERROR")
    assert msg.startswith("username")
    assert db_rows() == []


@pytest.mark.parametrize("username", ["abc", "a" * 50, "A_b.9", "..."])
def test_register_username_boundaries_ok(client, username):
    assert client.post("/api/register", json={"username": username, "password": "abcdef"}).status_code == 201


@pytest.mark.parametrize("pw", [None, "", "12345", "a" * 73, 123456, ["abcdef"], {"a": 1}, "é" * 37])
def test_register_invalid_password(client, pw):
    body = {"username": "validuser"}
    if pw is not None:
        body["password"] = pw
    assert err(client.post("/api/register", json=body), 400, "VALIDATION_ERROR").startswith("password")
    assert db_rows() == []


def test_register_missing_password_key(client):
    err(client.post("/api/register", json={"username": "validuser"}), 400, "VALIDATION_ERROR")


@pytest.mark.parametrize("pw", ["a" * 6, "a" * 72, "é" * 36, "mật khẩu dài 6+", "p\x00ssword"])
def test_register_password_boundaries_ok(client, pw):
    assert client.post("/api/register", json={"username": "validuser", "password": pw}).status_code == 201
    r = client.post("/api/login", json={"username": "validuser", "password": pw})
    assert r.status_code == 200


@pytest.mark.parametrize("email", ["abc", "a@b", "a b@c.d", "@c.d", "a@@c.d", "a@c.", 123, ["a@b.c"], "a" * 95 + "@b.com"])
def test_register_invalid_email(client, valid_user, email):
    valid_user["email"] = email
    assert err(client.post("/api/register", json=valid_user), 400, "VALIDATION_ERROR") == "email không hợp lệ"
    assert db_rows() == []


def test_register_email_100_chars_ok(client, valid_user):
    valid_user["email"] = "a" * (100 - len("@b.com")) + "@b.com"
    assert len(valid_user["email"]) == 100
    assert client.post("/api/register", json=valid_user).status_code == 201


@pytest.mark.parametrize("raw", [b"", b"not json", b"{bad", b"[]", b'"x"', b"123", b"null"])
def test_register_bad_body(client, raw):
    r = client.post("/api/register", content=raw, headers={"Content-Type": "application/json"})
    err(r, 400, "VALIDATION_ERROR")
    assert "detail" not in r.json()


def test_register_without_content_type_header(client, valid_user):
    import json
    r = client.post("/api/register", content=json.dumps(valid_user))
    assert r.status_code == 201


def test_register_duplicate_username_409(client, valid_user):
    assert client.post("/api/register", json=valid_user).status_code == 201
    err(client.post("/api/register", json=valid_user), 409, "CONFLICT")
    assert len(db_rows()) == 1


def test_register_duplicate_is_case_insensitive_like_mysql(client, valid_user):
    client.post("/api/register", json=valid_user)
    err(client.post("/api/register", json={**valid_user, "username": "ALICE_01"}), 409, "CONFLICT")


def test_register_race_condition_maps_unique_violation_to_409(client, valid_user, monkeypatch):
    client.post("/api/register", json=valid_user)
    monkeypatch.setattr(UserRepository, "find_by_username", lambda self, u: None)  # bỏ qua pre-check
    err(client.post("/api/register", json=valid_user), 409, "CONFLICT")
    assert len(db_rows()) == 1


def test_db_enforces_unique_username(client):
    with sqlite3.connect(config.DB_PATH) as c:
        c.execute("INSERT INTO users (username, password_hash) VALUES ('dup', 'x')")
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("INSERT INTO users (username, password_hash) VALUES ('DUP', 'y')")


# ------------------------------------------------------------------ login
def test_login_ok(client, valid_user):
    client.post("/api/register", json=valid_user)
    r = client.post("/api/login", json={"username": "alice_01", "password": "Secret1"})
    assert r.status_code == 200
    assert r.json() == {"status": "success", "data": {"id": 1, "username": "alice_01", "role": "USER", "token": "demo-token-alice_01"}}
    no_secret(r)


def test_login_username_case_insensitive_returns_canonical_name(client, valid_user):
    client.post("/api/register", json=valid_user)
    r = client.post("/api/login", json={"username": " ALICE_01 ", "password": "Secret1"})
    assert r.status_code == 200 and r.json()["data"]["username"] == "alice_01"
    assert r.json()["data"]["token"] == "demo-token-alice_01"


def test_login_wrong_password_and_unknown_user_same_error(client, valid_user):
    client.post("/api/register", json=valid_user)
    wrong = client.post("/api/login", json={"username": "alice_01", "password": "Wrong123"})
    unknown = client.post("/api/login", json={"username": "ghost", "password": "Secret1"})
    m1 = err(wrong, 401, "UNAUTHORIZED")
    m2 = err(unknown, 401, "UNAUTHORIZED")
    assert m1 == m2 and wrong.json() == unknown.json()


def test_login_password_is_case_sensitive(client, valid_user):
    client.post("/api/register", json=valid_user)
    err(client.post("/api/login", json={"username": "alice_01", "password": "secret1"}), 401, "UNAUTHORIZED")


def test_login_overlong_password_is_401_not_500(client, valid_user):
    client.post("/api/register", json=valid_user)
    err(client.post("/api/login", json={"username": "alice_01", "password": "a" * 200}), 401, "UNAUTHORIZED")


@pytest.mark.parametrize("body", [
    {}, {"username": "a"}, {"password": "x"}, {"username": "", "password": "x"}, {"username": "  ", "password": "x"},
    {"username": "a", "password": ""}, {"username": 1, "password": "x"}, {"username": "a", "password": 1},
    {"username": None, "password": None},
])
def test_login_missing_fields_400(client, body):
    assert err(client.post("/api/login", json=body), 400, "VALIDATION_ERROR") == "Thiếu username hoặc password"


@pytest.mark.parametrize("raw", [b"", b"oops", b"[]"])
def test_login_bad_body(client, raw):
    err(client.post("/api/login", content=raw, headers={"Content-Type": "application/json"}), 400, "VALIDATION_ERROR")


def test_login_sql_injection_attempt_fails(client, valid_user):
    client.post("/api/register", json=valid_user)
    err(client.post("/api/login", json={"username": "' OR '1'='1", "password": "x"}), 401, "UNAUTHORIZED")
    err(client.post("/api/login", json={"username": "alice_01' --", "password": "x"}), 401, "UNAUTHORIZED")


def test_login_corrupt_hash_is_401(client):
    with sqlite3.connect(config.DB_PATH) as c:
        c.execute("INSERT INTO users (username, password_hash, role) VALUES ('broken', 'not-a-hash', 'USER')")
    err(client.post("/api/login", json={"username": "broken", "password": "whatever"}), 401, "UNAUTHORIZED")


# ------------------------------------------------------------------ seed (3 tài khoản mẫu)
@pytest.mark.parametrize("username,password,role,uid", [
    ("admin", "Admin@123", "ADMIN", 1), ("user1", "User@123", "USER", 2), ("user2", "User@123", "USER", 3),
])
def test_seed_accounts_login_with_existing_bcrypt_hashes(seeded_client, username, password, role, uid):
    r = seeded_client.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200
    assert r.json()["data"] == {"id": uid, "username": username, "role": role, "token": f"demo-token-{username}"}
    err(seeded_client.post("/api/login", json={"username": username, "password": "Wrong@123"}), 401, "UNAUTHORIZED")


def test_seed_hashes_match_legacy_seed_file():
    from pathlib import Path

    from app.db import SEED_SQL

    legacy = Path(__file__).resolve().parents[3] / "database" / "user" / "seed.sql"
    if not legacy.exists():
        pytest.skip("không có database/user/seed.sql trong workspace")
    legacy_hashes = set(re.findall(r"\$2a\$10\$[./A-Za-z0-9]{53}", legacy.read_text(encoding="utf-8")))
    new_hashes = set(re.findall(r"\$2a\$10\$[./A-Za-z0-9]{53}", SEED_SQL.read_text(encoding="utf-8")))
    assert len(legacy_hashes) == 2 and new_hashes == legacy_hashes


def test_seed_is_idempotent_and_never_overwrites(client):
    from app.db import run_seed

    assert run_seed() == 3
    assert run_seed() == 0
    with sqlite3.connect(config.DB_PATH) as c:
        c.execute("UPDATE users SET email = 'changed@x.com' WHERE id = 2")
    run_seed()
    assert db_rows()[1][3] == "changed@x.com"
    assert len(db_rows()) == 3


def test_new_user_after_seed_gets_id_4(seeded_client, valid_user):
    assert seeded_client.post("/api/register", json=valid_user).json()["data"]["id"] == 4


def test_init_schema_is_idempotent_and_keeps_data(seeded_client):
    from app.db import init_schema

    init_schema()
    init_schema()
    assert len(db_rows()) == 3


def test_schema_and_seed_have_no_destructive_sql():
    from app.db import SCHEMA_SQL, SEED_SQL

    for f in (SCHEMA_SQL, SEED_SQL):
        sql = f.read_text(encoding="utf-8").upper()
        assert "DROP " not in sql and "DELETE " not in sql and "TRUNCATE" not in sql


# ------------------------------------------------------------------ users list / filter / detail
def test_list_empty(client):
    r = client.get("/api/users")
    assert r.status_code == 200 and r.json() == {"status": "success", "data": []}


def test_list_users_shape_order_and_no_secrets(seeded_client):
    r = seeded_client.get("/api/users")
    assert r.status_code == 200
    data = r.json()["data"]
    assert [u["id"] for u in data] == [1, 2, 3]
    assert data[0] == {"id": 1, "username": "admin", "email": "admin@cinema.local", "role": "ADMIN"}
    assert all(set(u) == {"id", "username", "email", "role"} for u in data)
    no_secret(r)


def test_filter_username_found(seeded_client):
    r = seeded_client.get("/api/users", params={"username": "user1"})
    assert r.status_code == 200
    assert r.json()["data"] == [{"id": 2, "username": "user1", "email": "user1@cinema.local", "role": "USER"}]
    no_secret(r)


@pytest.mark.parametrize("name", ["nobody", "", "   ", "user", "user1 OR 1=1", "' OR '1'='1", "%", "user%"])
def test_filter_username_not_found_returns_empty_array(seeded_client, name):
    r = seeded_client.get("/api/users", params={"username": name})
    assert r.status_code == 200 and r.json() == {"status": "success", "data": []}


def test_filter_username_trimmed_and_case_insensitive(seeded_client):
    r = seeded_client.get("/api/users", params={"username": " USER1 "})
    assert [u["username"] for u in r.json()["data"]] == ["user1"]


def test_filter_never_returns_more_than_one(seeded_client):
    assert len(seeded_client.get("/api/users", params={"username": "user2"}).json()["data"]) == 1


def test_get_user_by_id(seeded_client):
    r = seeded_client.get("/api/users/2")
    assert r.status_code == 200
    assert r.json() == {"status": "success", "data": {"id": 2, "username": "user1", "email": "user1@cinema.local", "role": "USER"}}
    no_secret(r)


def test_get_user_null_email(client):
    client.post("/api/register", json={"username": "noemail", "password": "abcdef"})
    assert client.get("/api/users/1").json()["data"]["email"] is None


@pytest.mark.parametrize("bad", ["abc", "1.5", "1e3", "0x1", "1_0", "%20", "٣", "99999999999999999999"])
def test_get_user_malformed_id_400(seeded_client, bad):
    err(seeded_client.get(f"/api/users/{bad}"), 400, "VALIDATION_ERROR")


@pytest.mark.parametrize("bad", ["0", "-1", "-999", "2147483648"])
def test_get_user_non_positive_or_overflow_id_400(seeded_client, bad):
    err(seeded_client.get(f"/api/users/{bad}"), 400, "VALIDATION_ERROR")


@pytest.mark.parametrize("missing", ["4", "999", "2147483647"])
def test_get_user_not_found_404(seeded_client, missing):
    err(seeded_client.get(f"/api/users/{missing}"), 404, "NOT_FOUND")


def test_get_user_sql_injection_in_path(seeded_client):
    err(seeded_client.get("/api/users/1 OR 1=1"), 400, "VALIDATION_ERROR")
    assert len(db_rows()) == 3


# ------------------------------------------------------------------ không lộ lỗi nội bộ
def test_db_failure_returns_500_envelope_without_leak(client, monkeypatch):
    def boom(self):
        raise sqlite3.OperationalError("no such table: users SELECT secret_column FROM users")

    monkeypatch.setattr(UserRepository, "find_all", boom)
    r = client.get("/api/users")
    err(r, 500, "INTERNAL_ERROR")
    assert "SELECT" not in r.text and "secret_column" not in r.text and "users" not in r.json()["message"]
    assert r.headers["access-control-allow-origin"] == "*"


def test_unexpected_exception_returns_500_without_traceback(client, monkeypatch):
    def boom(self, user_id):
        raise RuntimeError("internal path /srv/app/secret.py")

    monkeypatch.setattr(UserService, "get_user", boom)
    r = client.get("/api/users/1")
    err(r, 500, "INTERNAL_ERROR")
    assert "secret.py" not in r.text and "Traceback" not in r.text


def test_validation_error_does_not_echo_password(client):
    r = client.post("/api/register", json={"username": "ok_user", "password": "short", "email": "x"})
    assert "short" not in r.text
