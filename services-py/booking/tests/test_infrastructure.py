"""Test CSDL, múi giờ, cấu hình, vòng quét và công tắc JWT cuối kỳ."""
import asyncio
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app import main
from app.core import clock, config
from app.db import SCHEMA_SQL, SEED_SQL, init_schema, run_seed
from app.main import app

SECRET = "khoa-kiem-thu-du-dai-it-nhat-32-ky-tu"


def is_error(response, status, code):
    body = response.json()
    return response.status_code == status and body["status"] == "error" and body["code"] == code and body["message"]


# ------------------------------------------------------------------ schema + seed
def test_schema_is_idempotent_and_has_contract_columns(isolated_db):
    init_schema()
    init_schema()
    conn = sqlite3.connect(isolated_db)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(bookings)")]
    indexes = {row[1] for row in conn.execute("PRAGMA index_list(bookings)")}
    conn.close()
    assert columns == [
        "id", "movie_id", "showtime_id", "username", "seats", "total_price", "status", "created_at",
    ]
    assert {"idx_bookings_showtime_status", "idx_bookings_username"} <= indexes


@pytest.mark.parametrize(
    "column, value",
    [("status", "DONE"), ("total_price", -1)],
)
def test_database_rejects_invalid_values(isolated_db, column, value):
    init_schema()
    conn = sqlite3.connect(isolated_db)
    values = {"status": "PENDING", "total_price": 0, column: value}
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO bookings (movie_id, showtime_id, username, seats, total_price, status, created_at)"
            " VALUES (1, 1, 'u', 'A1', ?, ?, 'x')",
            (values["total_price"], values["status"]),
        )
    conn.close()


def test_seed_keeps_shared_ids_and_values_and_never_overwrites(isolated_db):
    init_schema()
    assert run_seed() == 3
    conn = sqlite3.connect(isolated_db)
    conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE id = 3")
    conn.commit()
    assert run_seed() == 0  # chạy lại không nhân đôi, không ghi đè
    rows = conn.execute(
        "SELECT id, movie_id, showtime_id, username, seats, total_price, status, created_at FROM bookings ORDER BY id"
    ).fetchall()
    conn.close()
    assert rows == [
        (1, 1, 1, "user1", "A1,A2", 180000, "PAID", "2026-10-01 10:00:00"),
        (2, 2, 3, "user2", "B5", 85000, "CANCELLED", "2026-10-01 11:00:00"),
        (3, 4, 5, "user1", "C3,C4", 180000, "CANCELLED", "2026-10-02 09:30:00"),
    ]


def test_new_order_id_starts_after_seed(seeded_client, order):
    seeded_client.get("/api/booking")
    assert seeded_client.post("/api/booking", json=order(seats=["Z1"])).json()["data"]["id"] == 4


def test_sql_files_contain_no_destructive_statement():
    for path in (SCHEMA_SQL, SEED_SQL):
        text = path.read_text(encoding="utf-8").upper()
        statements = [line for line in text.splitlines() if not line.startswith("--")]
        assert not any(word in " ".join(statements) for word in ("DROP ", "DELETE ", "TRUNCATE "))


def test_init_db_command_is_explicit_and_repeatable(isolated_db):
    service_dir = Path(__file__).resolve().parents[1]
    env = {"DB_PATH": str(isolated_db), "PYTHONIOENCODING": "utf-8", "SYSTEMROOT": "C:\\Windows"}
    for _ in range(2):
        done = subprocess.run(
            [sys.executable, "-m", "app.db.init_db", "--seed"], cwd=service_dir, env=env, capture_output=True
        )
        assert done.returncode == 0, done.stderr
    conn = sqlite3.connect(isolated_db)
    assert conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 3
    conn.close()


def test_app_startup_does_not_create_schema_or_data(isolated_db):
    with TestClient(app):
        pass
    assert not isolated_db.exists()


# ------------------------------------------------------------------ múi giờ
def test_clock_follows_app_timezone_not_machine_time(monkeypatch):
    """Lệch hẳn -3 giờ so với UTC để không thể trùng giờ máy (máy phát triển thường là UTC+7, container UTC)."""
    monkeypatch.setattr(clock, "ZoneInfo", lambda _: timezone(timedelta(hours=-3)))
    expected = datetime.now(timezone.utc) - timedelta(hours=3)
    assert abs(clock.now() - expected.replace(tzinfo=None)) < timedelta(seconds=5)


def test_clock_falls_back_to_utc_plus_7_without_timezone_database(monkeypatch):
    def missing(_):
        raise clock.ZoneInfoNotFoundError("no tzdata")

    monkeypatch.setattr(clock, "ZoneInfo", missing)
    expected = datetime.now(timezone.utc) + timedelta(hours=7)
    assert abs(clock.now() - expected.replace(tzinfo=None)) < timedelta(seconds=5)


def test_clock_has_whole_seconds():
    assert clock.now().microsecond == 0


def test_created_at_and_showtime_check_use_app_timezone(client, upstreams, order, monkeypatch):
    """Giờ chiếu vừa qua theo APP_TIMEZONE phải bị từ chối, và created_at ghi đúng múi giờ đó."""
    monkeypatch.setattr(clock, "ZoneInfo", lambda _: timezone(timedelta(hours=-3)))
    zone_now = datetime.now(timezone(timedelta(hours=-3))).replace(tzinfo=None)
    upstreams.showtimes[1]["time"] = clock.format_time(zone_now - timedelta(minutes=1))
    assert is_error(client.post("/api/booking", json=order()), 400, "SHOWTIME_CLOSED")
    upstreams.showtimes[1]["time"] = clock.format_time(zone_now + timedelta(minutes=5))
    created = client.post("/api/booking", json=order()).json()["data"]["createdAt"]
    assert abs(datetime.strptime(created, clock.TIME_FORMAT) - zone_now) < timedelta(seconds=5)


# ------------------------------------------------------------------ cấu hình
def test_dotenv_fills_missing_values_but_never_overrides_environment(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('# ghi chú\nBOOKING_TEST_A="tu-file"\nBOOKING_TEST_B=tu-file\ndong-sai\n', encoding="utf-8")
    monkeypatch.delenv("BOOKING_TEST_A", raising=False)
    monkeypatch.setenv("BOOKING_TEST_B", "tu-moi-truong")
    config._load_dotenv(str(env_file))
    import os

    assert os.environ["BOOKING_TEST_A"] == "tu-file"
    assert os.environ["BOOKING_TEST_B"] == "tu-moi-truong"
    del os.environ["BOOKING_TEST_A"]


def test_jwt_is_off_by_default():
    assert config.JWT_REQUIRED is False


# ------------------------------------------------------------------ vòng quét nền
def test_background_sweeper_cancels_expired_holds(client, upstreams, order, monkeypatch):
    booking = client.post("/api/booking", json=order(payNow=False)).json()["data"]
    stale = clock.format_time(clock.now() - timedelta(minutes=11))
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("UPDATE bookings SET created_at = ? WHERE id = ?", (stale, booking["id"]))
    conn.commit()
    conn.close()
    monkeypatch.setattr(main, "SWEEP_INTERVAL_SECONDS", 0.01)

    async def run_briefly():
        task = asyncio.create_task(main._sweep_expired_holds())
        await asyncio.sleep(0.1)
        task.cancel()

    asyncio.run(run_briefly())
    conn = sqlite3.connect(config.DB_PATH)
    assert conn.execute("SELECT status FROM bookings").fetchone()[0] == "CANCELLED"
    conn.close()


def test_background_sweeper_survives_database_errors(monkeypatch, caplog, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "chua-co-bang.db"))
    monkeypatch.setattr(main, "SWEEP_INTERVAL_SECONDS", 0.01)

    async def run_briefly():
        task = asyncio.create_task(main._sweep_expired_holds())
        await asyncio.sleep(0.05)
        alive = not task.done()
        task.cancel()
        return alive

    assert asyncio.run(run_briefly()) is True
    assert "Quét đơn quá hạn lỗi" in caplog.text


# ------------------------------------------------------------------ JWT cuối kỳ (JWT_REQUIRED=true)
def token(sub="user1", role="USER", secret=SECRET, **overrides):
    now = int(time.time())
    claims = {"sub": sub, "userId": 2, "role": role, "iat": now, "exp": now + 7200, **overrides}
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, secret, algorithm="HS256")


def bearer(*args, **kwargs):
    return {"Authorization": f"Bearer {token(*args, **kwargs)}"}


@pytest.fixture
def jwt_on(monkeypatch):
    monkeypatch.setattr(config, "JWT_REQUIRED", True)
    monkeypatch.setattr(config, "JWT_SECRET", SECRET)


def test_create_takes_username_from_token_not_body(client, jwt_on, order):
    r = client.post("/api/booking", json=order(username="user2"), headers=bearer("user1"))
    assert r.status_code == 201
    assert r.json()["data"]["username"] == "user1"


def test_create_works_without_username_in_body(client, jwt_on):
    body = {"movieId": 1, "showtimeId": 1, "seats": ["A1"]}  # đúng ví dụ §4.3 của kế hoạch v2.1
    assert client.post("/api/booking", json=body, headers=bearer("user1")).status_code == 201


def test_token_is_forwarded_to_payment(client, upstreams, jwt_on, order):
    headers = bearer("user1")
    client.post("/api/booking", json=order(), headers=headers)
    assert upstreams.service_calls("payment")[0].headers["authorization"] == headers["Authorization"]


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": ""},
        {"Authorization": "Bearer "},
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer demo-token-user1"},  # token giữa kỳ
        {"Authorization": f"Bearer {token(secret='khoa-khac-cung-du-dai-it-nhat-32-ky-tu')}"},
        {"Authorization": f"Bearer {token(exp=int(time.time()) - 3600)}"},
        {"Authorization": f"Bearer {token(role=None)}"},
    ],
)
def test_missing_or_bad_token_is_401_before_anything_happens(client, upstreams, jwt_on, order, headers):
    assert is_error(client.post("/api/booking", json=order(), headers=headers), 401, "UNAUTHORIZED")
    assert upstreams.calls == []


def test_token_expired_within_60_seconds_is_accepted(client, jwt_on, order):
    headers = {"Authorization": f"Bearer {token(exp=int(time.time()) - 30)}"}
    assert client.post("/api/booking", json=order(), headers=headers).status_code == 201


def test_short_secret_fails_closed(client, jwt_on, order, monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "ngan")
    headers = {"Authorization": f"Bearer {token(secret='ngan')}"}
    assert is_error(client.post("/api/booking", json=order(), headers=headers), 401, "UNAUTHORIZED")


def test_list_all_requires_admin(client, jwt_on):
    assert client.get("/api/booking", headers=bearer("admin", "ADMIN")).status_code == 200
    assert is_error(client.get("/api/booking", headers=bearer("user1")), 403, "FORBIDDEN")
    assert is_error(client.get("/api/booking"), 401, "UNAUTHORIZED")


def test_user_can_list_only_own_tickets_for_client_page(client, jwt_on):
    assert client.get("/api/booking?username=user1", headers=bearer("user1")).status_code == 200
    assert is_error(client.get("/api/booking?username=user2", headers=bearer("user1")), 403, "FORBIDDEN")


def test_detail_requires_owner_or_admin(client, jwt_on, order):
    client.post("/api/booking", json=order(), headers=bearer("user1"))
    assert client.get("/api/booking/1", headers=bearer("user1")).status_code == 200
    assert client.get("/api/booking/1", headers=bearer("admin", "ADMIN")).status_code == 200
    assert is_error(client.get("/api/booking/1", headers=bearer("user2")), 403, "FORBIDDEN")
    assert is_error(client.get("/api/booking/1"), 401, "UNAUTHORIZED")


def test_pay_uses_token_identity_not_body(client, jwt_on, order):
    client.post("/api/booking", json=order(payNow=False), headers=bearer("user1"))
    forged = {"username": "user1", "paymentMethod": "MOMO"}
    assert is_error(client.post("/api/booking/1/pay", json=forged, headers=bearer("user2")), 403, "FORBIDDEN")
    r = client.post("/api/booking/1/pay", json={"paymentMethod": "MOMO"}, headers=bearer("user1"))
    assert r.json()["data"]["status"] == "PAID"


def test_admin_can_cancel_customer_order_like_admin_page_does(client, jwt_on, order):
    client.post("/api/booking", json=order(payNow=False), headers=bearer("user1"))
    r = client.post("/api/booking/1/cancel", json={"username": "user1"}, headers=bearer("admin", "ADMIN"))
    assert r.json()["data"]["status"] == "CANCELLED"


def test_user_cannot_cancel_someone_elses_order_with_token(client, jwt_on, order):
    client.post("/api/booking", json=order(payNow=False), headers=bearer("user1"))
    r = client.post("/api/booking/1/cancel", json={"username": "user1"}, headers=bearer("user2"))
    assert is_error(r, 403, "FORBIDDEN")


def test_update_uses_token_identity_not_body(client, jwt_on, order):
    client.post("/api/booking", json=order(payNow=False), headers=bearer("user1"))
    forged = {"username": "user1", "seats": ["A3"]}
    assert is_error(client.put("/api/booking/1", json=forged, headers=bearer("user2")), 403, "FORBIDDEN")
    assert is_error(client.put("/api/booking/1", json=forged), 401, "UNAUTHORIZED")
    r = client.put("/api/booking/1", json={"seats": ["A3"]}, headers=bearer("user1"))
    assert r.json()["data"]["seats"] == ["A3"]
    r = client.put("/api/booking/1", json={"seats": ["A4"]}, headers=bearer("admin", "ADMIN"))
    assert r.json()["data"]["seats"] == ["A4"]


def test_delete_uses_token_identity_not_query(client, jwt_on, order):
    client.post("/api/booking", json=order(payNow=False, seats=["A1"]), headers=bearer("user1"))
    client.post("/api/booking", json=order(payNow=False, seats=["A2"]), headers=bearer("user1"))
    assert is_error(client.delete("/api/booking/1?username=user1", headers=bearer("user2")), 403, "FORBIDDEN")
    assert is_error(client.delete("/api/booking/1?username=user1"), 401, "UNAUTHORIZED")
    assert client.delete("/api/booking/1", headers=bearer("user1")).status_code == 200
    assert client.delete("/api/booking/2", headers=bearer("admin", "ADMIN")).status_code == 200


def test_seat_map_stays_public_with_jwt_on(client, jwt_on):
    assert client.get("/api/booking/seats?showtimeId=1").status_code == 200
    assert client.get("/api/booking/availability?showtimeIds=1").status_code == 200
    assert client.get("/health").status_code == 200


def test_jwt_off_ignores_token_and_keeps_baseline(client, order):
    assert client.post("/api/booking", json=order(), headers={"Authorization": "Bearer rac"}).status_code == 201
