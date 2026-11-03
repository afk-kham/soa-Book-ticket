"""CRUD /api/users cho Admin: tạo (chọn role), sửa một phần, xóa; chặn xóa/hạ quyền ADMIN cuối cùng."""
import bcrypt

from tests.test_user_api import db_rows, err, no_secret


def test_create_user_with_role_201(seeded_client):
    r = seeded_client.post("/api/users", json={"username": "staff_01", "password": "Secret1", "role": "admin"})
    assert r.status_code == 201
    d = r.json()["data"]
    assert d == {"id": 4, "username": "staff_01", "email": None, "role": "ADMIN"}
    no_secret(r)
    assert seeded_client.post("/api/users", json={"username": "u_default", "password": "Secret1"}).json()["data"]["role"] == "USER"


def test_create_user_errors(seeded_client):
    err(seeded_client.post("/api/users", json={"username": "user1", "password": "Secret1"}), 409, "CONFLICT")
    err(seeded_client.post("/api/users", json={"username": "x_1", "password": "Secret1", "role": "ROOT"}), 400, "VALIDATION_ERROR")
    err(seeded_client.post("/api/users", json={"username": "a", "password": "Secret1"}), 400, "VALIDATION_ERROR")
    err(seeded_client.post("/api/users", json={"username": "abc", "password": "123"}), 400, "VALIDATION_ERROR")


def test_update_partial_fields(seeded_client):
    uid = seeded_client.get("/api/users?username=user2").json()["data"][0]["id"]
    r = seeded_client.put(f"/api/users/{uid}", json={"email": "new@mail.vn", "role": "ADMIN"})
    assert r.status_code == 200
    assert r.json()["data"] == {"id": uid, "username": "user2", "email": "new@mail.vn", "role": "ADMIN"}
    no_secret(r)
    d = seeded_client.patch(f"/api/users/{uid}", json={"username": "user2_new", "email": ""}).json()["data"]
    assert d["username"] == "user2_new" and d["email"] is None and d["role"] == "ADMIN"
    assert seeded_client.put(f"/api/users/{uid}", json={}).json()["data"]["username"] == "user2_new"


def test_update_password_rehashes_and_login_works(seeded_client):
    uid = seeded_client.get("/api/users?username=user1").json()["data"][0]["id"]
    assert seeded_client.put(f"/api/users/{uid}", json={"password": "NewPass9"}).status_code == 200
    row = [r for r in db_rows() if r[0] == uid][0]
    assert row[2].startswith("$2a$") and bcrypt.checkpw(b"NewPass9", row[2].encode())
    assert seeded_client.post("/api/login", json={"username": "user1", "password": "NewPass9"}).status_code == 200
    err(seeded_client.post("/api/login", json={"username": "user1", "password": "User@123"}), 401, "UNAUTHORIZED")


def test_update_errors(seeded_client):
    err(seeded_client.put("/api/users/999", json={"email": "a@b.vn"}), 404, "NOT_FOUND")
    err(seeded_client.put("/api/users/abc", json={}), 400, "VALIDATION_ERROR")
    err(seeded_client.put("/api/users/0", json={}), 400, "VALIDATION_ERROR")
    uid = seeded_client.get("/api/users?username=user1").json()["data"][0]["id"]
    err(seeded_client.put(f"/api/users/{uid}", json={"username": "USER2"}), 409, "CONFLICT")  # NOCASE
    err(seeded_client.put(f"/api/users/{uid}", json={"role": "BOSS"}), 400, "VALIDATION_ERROR")
    err(seeded_client.put(f"/api/users/{uid}", json={"email": "sai"}), 400, "VALIDATION_ERROR")
    err(seeded_client.put(f"/api/users/{uid}", json={"password": "12"}), 400, "VALIDATION_ERROR")
    assert seeded_client.put(f"/api/users/{uid}", json={"username": "User1"}).status_code == 200  # đổi hoa/thường chính mình


def test_delete_user(seeded_client):
    uid = seeded_client.get("/api/users?username=user2").json()["data"][0]["id"]
    r = seeded_client.delete(f"/api/users/{uid}")
    assert r.status_code == 200 and r.json()["data"] == {"id": uid, "deleted": True}
    err(seeded_client.get(f"/api/users/{uid}"), 404, "NOT_FOUND")
    err(seeded_client.delete(f"/api/users/{uid}"), 404, "NOT_FOUND")
    err(seeded_client.delete("/api/users/abc"), 400, "VALIDATION_ERROR")


def test_last_admin_cannot_be_deleted_or_demoted(seeded_client):
    admin_id = seeded_client.get("/api/users?username=admin").json()["data"][0]["id"]
    err(seeded_client.delete(f"/api/users/{admin_id}"), 409, "CONFLICT")
    err(seeded_client.put(f"/api/users/{admin_id}", json={"role": "USER"}), 409, "CONFLICT")
    seeded_client.post("/api/users", json={"username": "admin2", "password": "Secret1", "role": "ADMIN"})
    assert seeded_client.put(f"/api/users/{admin_id}", json={"role": "USER"}).status_code == 200
    assert seeded_client.delete(f"/api/users/{admin_id}").status_code == 200


def test_cors_allows_crud_methods(client):
    r = client.options("/api/users/1", headers={"Origin": "http://localhost:8081", "Access-Control-Request-Method": "DELETE"})
    assert r.status_code == 204
    assert all(m in r.headers["access-control-allow-methods"] for m in ("PUT", "PATCH", "DELETE"))
