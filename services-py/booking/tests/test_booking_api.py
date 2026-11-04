"""Test hợp đồng API_CONTRACT §5: envelope, camelCase, mã HTTP, mã lỗi, kiểm tra đầu vào."""
import json

import pytest

from app.core import config


def is_error(response, status, code):
    body = response.json()
    return response.status_code == status and body["status"] == "error" and body["code"] == code and body["message"]


# ------------------------------------------------------------------ POST /api/booking
def test_create_pays_and_notifies(client, upstreams, order):
    r = client.post("/api/booking", json=order())
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "success"
    data = body["data"]
    assert data["id"] == 1
    assert data["movieId"] == 1
    assert data["showtimeId"] == 1
    assert data["username"] == "user1"
    assert data["seats"] == ["A1", "A2"]
    assert data["totalPrice"] == 180000  # 90000 lấy từ Showtime x 2 ghế
    assert data["status"] == "PAID"
    assert data["expiresAt"] is None
    assert data["payment"] == {"status": "PAID", "method": "MOMO", "transactionId": "1"}
    assert data["notification"] == "SENT"


def test_result_has_exact_contract_fields(client, order):
    data = client.post("/api/booking", json=order()).json()["data"]
    assert list(data) == [
        "id", "movieId", "showtimeId", "username", "seats", "totalPrice", "status",
        "createdAt", "expiresAt", "payment", "notification",
    ]


def test_create_calls_partners_in_contract_order(client, upstreams, order):
    client.post("/api/booking", json=order())
    assert [r.url.port for r in upstreams.calls] == [5003, 5001, 5002, 5005, 5006]


def test_payment_receives_server_side_amount_not_client_price(client, upstreams, order):
    client.post("/api/booking", json=order(pricePerSeat=1, totalPrice=1))
    sent = json.loads(upstreams.service_calls("payment")[0].content)
    assert sent == {"bookingId": 1, "amount": 180000, "method": "MOMO"}


def test_notification_gets_only_fields_it_accepts(client, upstreams, order):
    client.post("/api/booking", json=order())
    sent = json.loads(upstreams.service_calls("notification")[0].content)
    assert sent == {"username": "user1", "bookingId": 1, "channel": "EMAIL"}  # Notification từ chối trường lạ


def test_username_with_special_characters_is_escaped_in_query(client, upstreams, order):
    upstreams.users.add("a b&c")
    assert client.post("/api/booking", json=order(username="a b&c")).status_code == 201
    assert upstreams.service_calls("user")[0].url.params["username"] == "a b&c"


@pytest.mark.parametrize("key", ["paymentMethod", "method"])
def test_payment_method_accepts_both_names_and_any_case(client, order, key):
    data = client.post("/api/booking", json=order(**{key: " vnpay "})).json()["data"]
    assert data["payment"]["method"] == "VNPAY"


def test_payment_method_prefers_new_name(client, order):
    data = client.post("/api/booking", json=order(paymentMethod="CASH", method="MOMO")).json()["data"]
    assert data["payment"]["method"] == "CASH"


def test_seats_are_normalized_to_upper_case(client, order):
    data = client.post("/api/booking", json=order(seats=[" a1 ", "b12"])).json()["data"]
    assert data["seats"] == ["A1", "B12"]


def test_username_is_trimmed(client, order):
    assert client.post("/api/booking", json=order(username="  user1 ")).json()["data"]["username"] == "user1"


@pytest.mark.parametrize(
    "overrides, message_part",
    [
        ({"username": None}, "username"),
        ({"username": "   "}, "username"),
        ({"username": 123}, "username"),
        ({"username": "x" * 51}, "username"),
        ({"movieId": None}, "movieId"),
        ({"movieId": "1"}, "movieId"),
        ({"movieId": 1.5}, "movieId"),
        ({"movieId": True}, "movieId"),
        ({"movieId": 0}, "movieId"),
        ({"movieId": -1}, "movieId"),
        ({"movieId": 2147483648}, "movieId"),
        ({"showtimeId": None}, "showtimeId"),
        ({"showtimeId": "abc"}, "showtimeId"),
        ({"seats": None}, "seats"),
        ({"seats": "A1"}, "seats"),
        ({"seats": []}, "1 đến 10"),
        ({"seats": ["A1", "A1"]}, "trùng"),
        ({"seats": ["a1", "A1"]}, "trùng"),
        ({"seats": ["zz"]}, "Mã ghế"),
        ({"seats": ["A100"]}, "Mã ghế"),
        ({"seats": ["1A"]}, "Mã ghế"),
        ({"seats": [1]}, "Mã ghế"),
        ({"seats": ["A1\nB2"]}, "Mã ghế"),
        ({"seats": [f"A{i}" for i in range(1, 12)]}, "1 đến 10"),
    ],
)
def test_invalid_body_is_rejected_before_calling_anyone(client, upstreams, order, overrides, message_part):
    r = client.post("/api/booking", json=order(**overrides))
    assert is_error(r, 400, "VALIDATION_ERROR")
    assert message_part in r.json()["message"]
    assert upstreams.calls == []


def test_ten_seats_is_allowed(client, order):
    seats = [f"A{i}" for i in range(1, 11)]
    assert client.post("/api/booking", json=order(seats=seats)).json()["data"]["totalPrice"] == 900000


@pytest.mark.parametrize(
    "raw, message",
    [
        (b"", "Body yêu cầu rỗng"),
        (b"{not json", "JSON không hợp lệ"),
        (b"\xff\xfe\x00", "JSON không hợp lệ"),
        (b'{"movieId": NaN}', "JSON không hợp lệ"),
        (b"[" * 60000, "JSON không hợp lệ"),
        (b"[1,2]", "Body phải là một đối tượng JSON"),
        (b'"text"', "Body phải là một đối tượng JSON"),
        (b"null", "Body phải là một đối tượng JSON"),
    ],
)
@pytest.mark.parametrize("path", ["/api/booking", "/api/booking/1/pay", "/api/booking/1/cancel"])
def test_malformed_body_never_crashes(client, path, raw, message):
    r = client.post(path, content=raw, headers={"Content-Type": "application/json"})
    assert is_error(r, 400, "VALIDATION_ERROR")
    assert r.json()["message"] == message


def test_body_over_64_kib_is_413(client, order):
    r = client.post("/api/booking", content=b" " * (64 * 1024 + 1))
    assert is_error(r, 413, "PAYLOAD_TOO_LARGE")


def test_body_of_exactly_64_kib_is_accepted(client, order):
    raw = json.dumps(order()).encode()
    assert client.post("/api/booking", content=raw + b" " * (64 * 1024 - len(raw))).status_code == 201


def test_body_without_content_type_is_accepted(client, order):
    assert client.post("/api/booking", content=json.dumps(order()).encode()).status_code == 201


# ------------------------------------------------------------------ GET /api/booking
def test_list_empty_is_empty_array_not_404(client):
    r = client.get("/api/booking")
    assert r.status_code == 200
    assert r.json() == {"status": "success", "data": []}


def test_list_item_has_no_payment_fields_and_is_sorted_by_id(client, order):
    client.post("/api/booking", json=order(seats=["A1"]))
    client.post("/api/booking", json=order(seats=["A2"]))
    data = client.get("/api/booking").json()["data"]
    assert [b["id"] for b in data] == [1, 2]
    assert list(data[0]) == [
        "id", "movieId", "showtimeId", "username", "seats", "totalPrice", "status", "createdAt", "expiresAt",
    ]


def test_list_filters(client, order):
    client.post("/api/booking", json=order(seats=["A1"]))
    client.post("/api/booking", json=order(username="user2", seats=["A2"], payNow=False))
    client.post("/api/booking", json=order(movieId=2, showtimeId=2, seats=["A1"]))

    assert [b["id"] for b in client.get("/api/booking?username=user2").json()["data"]] == [2]
    assert [b["id"] for b in client.get("/api/booking?status=pending").json()["data"]] == [2]
    assert [b["id"] for b in client.get("/api/booking?showtimeId=2").json()["data"]] == [3]
    assert [b["id"] for b in client.get("/api/booking?username=user1&status=PAID&showtimeId=1").json()["data"]] == [1]


def test_list_username_filter_ignores_case_like_mysql_collation(client, order):
    client.post("/api/booking", json=order())
    assert len(client.get("/api/booking?username=USER1").json()["data"]) == 1


@pytest.mark.parametrize("query", ["username=", "username=%20", "showtimeId="])
def test_list_blank_filters_are_ignored(client, order, query):
    client.post("/api/booking", json=order())
    assert len(client.get(f"/api/booking?{query}").json()["data"]) == 1


@pytest.mark.parametrize("query", ["status=DONE", "status=", "showtimeId=abc", "showtimeId=0", "showtimeId=-1"])
def test_list_invalid_filter_is_400(client, query):
    assert is_error(client.get(f"/api/booking?{query}"), 400, "VALIDATION_ERROR")


# ------------------------------------------------------------------ GET /api/booking/{id}
def test_get_detail(client, order):
    client.post("/api/booking", json=order())
    r = client.get("/api/booking/1")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "PAID"
    assert "payment" not in r.json()["data"]


@pytest.mark.parametrize("booking_id", ["99999", "2147483648", str(2**70)])
def test_get_unknown_id_is_404(client, booking_id):
    assert is_error(client.get(f"/api/booking/{booking_id}"), 404, "NOT_FOUND")


def test_get_non_numeric_id_is_endpoint_404(client):
    assert is_error(client.get("/api/booking/abc"), 404, "NOT_FOUND")


# ------------------------------------------------------------------ GET /api/booking/seats
def test_seats_sorted_and_cancelled_excluded(client, order):
    client.post("/api/booking", json=order(seats=["B2", "A10", "A2"]))
    client.post("/api/booking", json=order(seats=["C1"], payNow=False))
    client.post("/api/booking", json=order(seats=["D1"], paymentMethod="KHONGHOPLE"))
    r = client.get("/api/booking/seats?showtimeId=1")
    assert r.status_code == 200
    assert r.json()["data"] == {"showtimeId": 1, "seats": ["A10", "A2", "B2", "C1"]}  # sắp tăng theo chuỗi


def test_seats_of_empty_showtime(client):
    assert client.get("/api/booking/seats?showtimeId=7").json()["data"] == {"showtimeId": 7, "seats": []}


@pytest.mark.parametrize("query", ["", "?showtimeId=", "?showtimeId=abc", "?showtimeId=0", "?showtimeId=2147483648"])
def test_seats_invalid_showtime_is_400(client, query):
    assert is_error(client.get(f"/api/booking/seats{query}"), 400, "VALIDATION_ERROR")


# ------------------------------------------------------------------ GET /api/booking/availability
def test_availability_counts_seats_keeps_order_and_drops_duplicates(client, order):
    client.post("/api/booking", json=order(seats=["A1", "A2"]))
    client.post("/api/booking", json=order(seats=["B1"], payNow=False))
    client.post("/api/booking", json=order(seats=["C1"], paymentMethod="KHONGHOPLE"))
    r = client.get("/api/booking/availability?showtimeIds=9, 1,9,,")
    assert r.status_code == 200
    assert r.json()["data"] == [{"showtimeId": 9, "taken": 0}, {"showtimeId": 1, "taken": 3}]


def test_availability_accepts_500_ids(client):
    ids = ",".join(str(i) for i in range(1, 501))
    assert len(client.get(f"/api/booking/availability?showtimeIds={ids}").json()["data"]) == 500


@pytest.mark.parametrize("query", ["", "?showtimeIds=", "?showtimeIds=,", "?showtimeIds=1,abc", "?showtimeIds=0"])
def test_availability_invalid_is_400(client, query):
    assert is_error(client.get(f"/api/booking/availability{query}"), 400, "VALIDATION_ERROR")


def test_availability_over_500_ids_is_400(client):
    ids = ",".join(str(i) for i in range(1, 502))
    assert is_error(client.get(f"/api/booking/availability?showtimeIds={ids}"), 400, "VALIDATION_ERROR")


# ------------------------------------------------------------------ hạ tầng HTTP
def test_health_pings_database(client):
    r = client.get("/health")
    assert r.json() == {"status": "success", "data": {"service": "booking-service", "port": 5004}}


def test_health_is_500_when_database_is_broken(client, monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path))  # một thư mục: sqlite không mở được
    r = client.get("/health")
    assert is_error(r, 500, "INTERNAL_ERROR")


def test_sql_error_details_never_leak(client, monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "chua-co-bang.db"))  # DB chưa chạy init_db
    r = client.get("/api/booking")
    assert is_error(r, 500, "INTERNAL_ERROR")
    assert r.json()["message"] == "Lỗi máy chủ nội bộ"
    assert "bookings" not in r.text and "sqlite" not in r.text.lower()


def test_unknown_path_is_404_envelope(client):
    r = client.get("/khong-co")
    assert is_error(r, 404, "NOT_FOUND")
    assert r.json()["message"] == "Endpoint không tồn tại"


@pytest.mark.parametrize(
    "method, path, allow",
    [
        ("put", "/api/booking", "GET, OPTIONS, POST"),
        ("delete", "/api/booking", "GET, OPTIONS, POST"),
        ("patch", "/api/booking/1", "DELETE, GET, OPTIONS, PUT"),
        ("put", "/api/booking/seats", "GET, OPTIONS"),
        ("delete", "/api/booking/availability", "GET, OPTIONS"),
        ("post", "/api/booking/seats", "GET, OPTIONS"),
        ("post", "/api/booking/availability", "GET, OPTIONS"),
        ("get", "/api/booking/1/pay", "OPTIONS, POST"),
        ("put", "/api/booking/1/cancel", "OPTIONS, POST"),
        ("post", "/health", "GET, OPTIONS"),
    ],
)
def test_wrong_method_is_405_with_allow_header(client, method, path, allow):
    r = getattr(client, method)(path)
    assert is_error(r, 405, "METHOD_NOT_ALLOWED")
    assert r.headers["allow"] == allow


@pytest.mark.parametrize("path", ["/api/booking", "/api/booking/1/pay", "/khong-co"])
def test_options_is_204_without_body(client, path):
    r = client.options(path, headers={"Origin": "http://x", "Access-Control-Request-Headers": "authorization"})
    assert r.status_code == 204
    assert r.content == b""
    assert r.headers["access-control-allow-origin"] == "*"
    assert "Authorization" in r.headers["access-control-allow-headers"]
    assert r.headers["access-control-allow-methods"] == "GET, POST, PUT, DELETE, OPTIONS"


@pytest.mark.parametrize("path", ["/health", "/api/booking", "/api/booking/99", "/khong-co"])
def test_every_response_has_cors_and_utf8_json(client, path):
    r = client.get(path)
    assert r.headers["access-control-allow-origin"] == "*"
    assert r.headers["content-type"] == "application/json; charset=utf-8"


def test_trailing_slash_behaves_like_no_slash(client, order):
    client.post("/api/booking/", json=order(), follow_redirects=False)
    assert client.get("/api/booking/", follow_redirects=False).status_code == 200
    assert client.get("/api/booking/1/", follow_redirects=False).status_code == 200


def test_openapi_documents_every_business_endpoint_and_request_body(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths) == {
        "/health",
        "/api/booking",
        "/api/booking/seats",
        "/api/booking/availability",
        "/api/booking/{booking_id}",
        "/api/booking/{booking_id}/pay",
        "/api/booking/{booking_id}/cancel",
    }
    properties = paths["/api/booking"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]
    assert {"username", "movieId", "showtimeId", "seats", "paymentMethod", "payNow"} == set(properties)
    detail = paths["/api/booking/{booking_id}"]
    assert {"get", "put", "delete"} == set(detail)
    assert {"username", "seats"} == set(detail["put"]["requestBody"]["content"]["application/json"]["schema"]["properties"])
    assert "username" in {p["name"] for p in detail["delete"]["parameters"]}
