"""Test nghiệp vụ điều phối: giữ ghế, thanh toán, hủy, hết hạn, đối tác sập (INTEGRATION_FLOW.md §2)."""
import asyncio
import json
import sqlite3
import threading
from datetime import timedelta

import httpx
import pytest

from app.api.deps import get_upstream
from app.core import clock, config
from app.core.errors import BookingError
from app.db import init_schema
from app.main import app
from app.repositories import BookingRepository
from app.services import BookingService, UpstreamClient


def is_error(response, status, code):
    body = response.json()
    return response.status_code == status and body["status"] == "error" and body["code"] == code and body["message"]


def rows(sql="SELECT * FROM bookings", *params):
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def age_booking(booking_id, minutes):
    """Lùi created_at để giả lập đơn đã giữ ghế từ ``minutes`` phút trước."""
    created = clock.format_time(clock.now() - timedelta(minutes=minutes))
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("UPDATE bookings SET created_at = ? WHERE id = ?", (created, booking_id))
    conn.commit()
    conn.close()


def hold(client, order, **overrides):
    return client.post("/api/booking", json=order(payNow=False, **overrides)).json()["data"]


def seats_of(client, showtime_id=1):
    return client.get(f"/api/booking/seats?showtimeId={showtime_id}").json()["data"]["seats"]


# ------------------------------------------------------------------ đối tác từ chối / không có dữ liệu
def test_unknown_user_is_404_and_nothing_saved(client, order):
    assert is_error(client.post("/api/booking", json=order(username="khong_co")), 404, "USER_NOT_FOUND")
    assert rows() == []


def test_unknown_movie_is_404_and_nothing_saved(client, order):
    assert is_error(client.post("/api/booking", json=order(movieId=99)), 404, "MOVIE_NOT_FOUND")
    assert rows() == []


def test_unknown_showtime_is_404_and_nothing_saved(client, order):
    assert is_error(client.post("/api/booking", json=order(showtimeId=99)), 404, "SHOWTIME_NOT_FOUND")
    assert rows() == []


def test_showtime_of_other_movie_is_400(client, order):
    r = client.post("/api/booking", json=order(showtimeId=2))
    assert is_error(r, 400, "VALIDATION_ERROR")
    assert "không thuộc phim" in r.json()["message"]
    assert rows() == []


def test_started_showtime_is_closed(client, order):
    assert is_error(client.post("/api/booking", json=order(showtimeId=3)), 400, "SHOWTIME_CLOSED")
    assert rows() == []


def test_showtime_starting_right_now_is_closed(client, upstreams, order):
    upstreams.showtimes[1]["time"] = clock.format_time(clock.now())
    assert is_error(client.post("/api/booking", json=order()), 400, "SHOWTIME_CLOSED")


def test_showtime_time_with_t_separator_is_understood(client, upstreams, order):
    upstreams.showtimes[1]["time"] = clock.format_time(clock.now() - timedelta(hours=1)).replace(" ", "T")
    assert is_error(client.post("/api/booking", json=order()), 400, "SHOWTIME_CLOSED")


def test_unparseable_showtime_time_does_not_block_booking(client, upstreams, order):
    upstreams.showtimes[1]["time"] = "không rõ"
    assert client.post("/api/booking", json=order()).status_code == 201


# ------------------------------------------------------------------ đối tác sập (503) / trả lỗi (502)
@pytest.mark.parametrize("service", ["user", "movie", "showtime"])
def test_lookup_partner_down_is_503_and_nothing_saved(client, upstreams, order, service):
    upstreams.down.add(service)
    assert is_error(client.post("/api/booking", json=order()), 503, f"{service.upper()}_SERVICE_UNAVAILABLE")
    assert rows() == []


@pytest.mark.parametrize("service", ["user", "movie", "showtime"])
def test_lookup_partner_error_is_502_and_nothing_saved(client, upstreams, order, service):
    upstreams.broken.add(service)
    assert is_error(client.post("/api/booking", json=order()), 502, f"{service.upper()}_SERVICE_ERROR")
    assert rows() == []


@pytest.mark.parametrize("field", ["price", "movieId"])
def test_malformed_showtime_is_502(client, upstreams, order, field):
    del upstreams.showtimes[1][field]
    assert is_error(client.post("/api/booking", json=order()), 502, "SHOWTIME_SERVICE_ERROR")


def test_partner_timeout_is_503(client, upstreams, order):
    def slow(request):
        raise httpx.ReadTimeout("too slow", request=request)

    upstreams._showtime = slow
    assert is_error(client.post("/api/booking", json=order()), 503, "SHOWTIME_SERVICE_UNAVAILABLE")


def test_partner_non_json_reply_uses_http_status_only(client, upstreams, order):
    upstreams._movie = lambda request: httpx.Response(500, text="<html>Bad Gateway</html>")
    assert is_error(client.post("/api/booking", json=order()), 502, "MOVIE_SERVICE_ERROR")


# ------------------------------------------------------------------ giữ ghế / chống đặt trùng
def test_taken_seat_is_409_and_names_the_seats(client, order):
    client.post("/api/booking", json=order(seats=["A1", "A2"]))
    r = client.post("/api/booking", json=order(username="user2", seats=["A2", "A1", "A3"]))
    assert is_error(r, 409, "SEAT_TAKEN")
    assert r.json()["message"] == "Ghế đã có người đặt: A2, A1"
    assert len(rows()) == 1


def test_lower_case_seat_cannot_bypass_taken_check(client, order):
    client.post("/api/booking", json=order(seats=["A1"]))
    assert is_error(client.post("/api/booking", json=order(seats=["a1"])), 409, "SEAT_TAKEN")


def test_held_seat_blocks_others(client, order):
    hold(client, order, seats=["A1"])
    assert is_error(client.post("/api/booking", json=order(username="user2", seats=["A1"])), 409, "SEAT_TAKEN")


def test_same_seat_on_other_showtime_is_free(client, order):
    client.post("/api/booking", json=order(seats=["A1"]))
    assert client.post("/api/booking", json=order(movieId=2, showtimeId=2, seats=["A1"])).status_code == 201


def test_concurrent_requests_for_same_seat_exactly_one_wins(upstreams, order):
    """Hai yêu cầu chạy xen kẽ qua các lần gọi đối tác, chỉ một yêu cầu được giữ ghế."""
    init_schema()

    async def interleaving(request):
        await asyncio.sleep(0)
        return upstreams(request)

    stub = UpstreamClient(httpx.MockTransport(interleaving))
    app.dependency_overrides[get_upstream] = lambda: stub

    async def race():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://booking") as http:
            return await asyncio.gather(
                *(http.post("/api/booking", json=order(seats=["A1"])) for _ in range(8))
            )

    try:
        replies = asyncio.run(race())
    finally:
        app.dependency_overrides.clear()
    assert sorted(r.status_code for r in replies) == [201] + [409] * 7
    assert len(rows("SELECT * FROM bookings WHERE status = 'PAID'")) == 1


def test_seat_transaction_is_atomic_across_threads(upstreams):
    """BEGIN IMMEDIATE vẫn bảo vệ khi nhiều luồng/tiến trình cùng ghi một file DB (ngoài event loop)."""
    init_schema()
    results, barrier = [], threading.Barrier(8)

    def attempt():
        service = BookingService(BookingRepository(), UpstreamClient(httpx.MockTransport(upstreams)))
        barrier.wait()
        try:
            results.append(service._hold_seats(1, 1, "user1", ["A1"], 90000).id)
        except BookingError as exc:
            results.append(exc.code)

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results.count("SEAT_TAKEN") == 7
    assert len(rows()) == 1


def test_transaction_takes_write_lock_from_the_start(isolated_db):
    """Quyền ghi phải giành ngay từ BEGIN, trước cả lần đọc đầu tiên; nếu không "đọc rồi ghi" sẽ không nguyên tử."""
    init_schema()
    with BookingRepository().transaction():
        other = sqlite3.connect(isolated_db, timeout=0)
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            other.execute("BEGIN IMMEDIATE")
        other.close()


# ------------------------------------------------------------------ Payment trong luồng đặt-và-trả-ngay
def test_payment_failed_cancels_order_releases_seats_and_skips_notification(client, upstreams, order):
    r = client.post("/api/booking", json=order(paymentMethod="KHONGHOPLE"))
    assert r.status_code == 201  # đơn đã được ghi nhận
    data = r.json()["data"]
    assert data["status"] == "CANCELLED"
    assert data["payment"] == {"status": "FAILED", "method": "KHONGHOPLE", "transactionId": "1"}
    assert data["notification"] == "SKIPPED"
    assert upstreams.service_calls("notification") == []
    assert seats_of(client) == []


def test_seat_can_be_rebooked_after_payment_failure(client, order):
    client.post("/api/booking", json=order(paymentMethod="KHONGHOPLE"))
    assert client.post("/api/booking", json=order()).json()["data"]["status"] == "PAID"


def test_payment_down_cancels_order_and_releases_seats(client, upstreams, order):
    upstreams.down.add("payment")
    r = client.post("/api/booking", json=order())
    assert is_error(r, 503, "PAYMENT_SERVICE_UNAVAILABLE")
    assert "Đơn #1 đã bị hủy" in r.json()["message"]
    assert rows()[0]["status"] == "CANCELLED"
    assert seats_of(client) == []
    assert upstreams.service_calls("notification") == []


def test_lost_payment_reply_is_recovered_by_asking_payment_again(client, upstreams, order):
    upstreams.lose_payment_reply = True
    r = client.post("/api/booking", json=order())
    assert r.status_code == 201
    assert r.json()["data"]["status"] == "PAID"
    assert r.json()["data"]["payment"]["transactionId"] == "1"
    assert r.json()["data"]["notification"] == "SENT"
    assert upstreams.service_calls("payment")[1].method == "GET"


def test_payment_error_status_is_502_and_cancels(client, upstreams, order):
    upstreams.broken.add("payment")
    r = client.post("/api/booking", json=order())
    assert is_error(r, 502, "PAYMENT_SERVICE_ERROR")
    assert "Lỗi máy chủ nội bộ" in r.json()["message"]  # lý do của Payment
    assert rows()[0]["status"] == "CANCELLED"


def test_payment_validation_rejection_is_502_and_cancels(client, upstreams, order):
    upstreams._payment = lambda request: httpx.Response(
        400, json={"status": "error", "code": "VALIDATION_ERROR", "message": "method là bắt buộc"}
    )
    assert is_error(client.post("/api/booking", json=order(paymentMethod="")), 502, "PAYMENT_SERVICE_ERROR")
    assert rows()[0]["status"] == "CANCELLED"


def test_payment_success_with_unexpected_body_is_502(client, upstreams, order):
    upstreams._payment = lambda request: httpx.Response(201, json={"status": "success", "data": []})
    assert is_error(client.post("/api/booking", json=order()), 502, "PAYMENT_SERVICE_ERROR")


def test_numeric_transaction_id_is_still_a_string_in_result(client, upstreams, order):
    def numeric_id(request):
        body = json.loads(request.content)
        return httpx.Response(201, json={"status": "success", "data": {"id": 7, "status": "PAID", **body}})

    upstreams._payment = numeric_id
    assert client.post("/api/booking", json=order()).json()["data"]["payment"]["transactionId"] == "7"


# ------------------------------------------------------------------ Notification best-effort
def test_notification_down_keeps_order_paid(client, upstreams, order):
    upstreams.down.add("notification")
    r = client.post("/api/booking", json=order())
    assert r.status_code == 201
    assert r.json()["data"]["status"] == "PAID"
    assert r.json()["data"]["notification"] == "FAILED"


def test_notification_error_status_keeps_order_paid(client, upstreams, order):
    upstreams.broken.add("notification")
    data = client.post("/api/booking", json=order()).json()["data"]
    assert (data["status"], data["notification"]) == ("PAID", "FAILED")


def test_internal_key_is_sent_only_when_configured(client, upstreams, order, monkeypatch):
    client.post("/api/booking", json=order(seats=["A1"]))
    assert "x-internal-key" not in upstreams.service_calls("notification")[0].headers
    monkeypatch.setattr(config, "INTERNAL_KEY", "khoa-noi-bo")
    client.post("/api/booking", json=order(seats=["A2"]))
    assert upstreams.service_calls("notification")[1].headers["x-internal-key"] == "khoa-noi-bo"


def test_authorization_header_is_forwarded_only_to_payment(client, upstreams, order):
    client.post("/api/booking", json=order(), headers={"Authorization": "Bearer abc"})
    assert upstreams.service_calls("payment")[0].headers["authorization"] == "Bearer abc"
    assert all("authorization" not in r.headers for r in upstreams.calls if r.url.port != 5005)


def test_non_ascii_authorization_header_does_not_strand_order(client, upstreams, order):
    raw = b"Bearer caf\xc3\xa9"  # TestClient luôn gửi header dạng UTF-8; Booking phải giữ nguyên từng byte
    r = client.post("/api/booking", json=order(), headers={"Authorization": raw})
    assert r.status_code == 201
    assert dict(upstreams.service_calls("payment")[0].headers.raw)[b"Authorization"] == raw


# ------------------------------------------------------------------ giữ ghế rồi trả sau
def test_hold_only_returns_pending_with_expiry_and_calls_no_payment(client, upstreams, order):
    r = client.post("/api/booking", json=order(payNow=False))
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["status"] == "PENDING"
    assert data["payment"] is None
    assert data["notification"] == "SKIPPED"
    assert upstreams.service_calls("payment") == []
    created = clock.format_time(clock.now())
    assert data["createdAt"][:16] == created[:16]
    expected = clock.datetime.strptime(data["createdAt"], clock.TIME_FORMAT) + timedelta(minutes=config.HOLD_MINUTES)
    assert data["expiresAt"] == clock.format_time(expected)


@pytest.mark.parametrize("value", [None, 0, "false", ""])
def test_only_literal_false_means_hold(client, order, value):
    assert client.post("/api/booking", json=order(payNow=value)).json()["data"]["status"] == "PAID"


def test_hold_minutes_is_configurable(client, order, monkeypatch):
    monkeypatch.setattr(config, "HOLD_MINUTES", 3)
    data = hold(client, order)
    created = clock.datetime.strptime(data["createdAt"], clock.TIME_FORMAT)
    assert data["expiresAt"] == clock.format_time(created + timedelta(minutes=3))


def test_pay_turns_hold_into_paid(client, upstreams, order):
    booking = hold(client, order)
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "bank_transfer"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "PAID"
    assert data["expiresAt"] is None
    assert data["payment"] == {"status": "PAID", "method": "BANK_TRANSFER", "transactionId": "1"}
    assert data["notification"] == "SENT"


def test_pay_accepts_old_method_name(client, order):
    booking = hold(client, order)
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "method": "MOMO"})
    assert r.json()["data"]["status"] == "PAID"


def test_failed_pay_keeps_hold_for_retry(client, upstreams, order):
    booking = hold(client, order)
    path = f"/api/booking/{booking['id']}/pay"
    r = client.post(path, json={"username": "user1", "paymentMethod": "KHONGHOPLE"})
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "PENDING"
    assert r.json()["data"]["payment"]["status"] == "FAILED"
    assert r.json()["data"]["notification"] == "SKIPPED"
    assert upstreams.service_calls("notification") == []
    assert client.post(path, json={"username": "user1", "paymentMethod": "MOMO"}).json()["data"]["status"] == "PAID"


def test_payment_down_during_pay_keeps_hold(client, upstreams, order):
    booking = hold(client, order)
    upstreams.down.add("payment")
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "MOMO"})
    assert is_error(r, 503, "PAYMENT_SERVICE_UNAVAILABLE")
    assert "bị hủy" not in r.json()["message"]
    assert rows()[0]["status"] == "PENDING"


def test_payment_error_during_pay_keeps_hold(client, upstreams, order):
    booking = hold(client, order)
    upstreams.broken.add("payment")
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "MOMO"})
    assert is_error(r, 502, "PAYMENT_SERVICE_ERROR")
    assert rows()[0]["status"] == "PENDING"


def test_pay_by_someone_else_is_403(client, upstreams, order):
    booking = hold(client, order)
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user2", "paymentMethod": "MOMO"})
    assert is_error(r, 403, "FORBIDDEN")
    assert upstreams.service_calls("payment") == []


def test_pay_owner_check_is_case_sensitive_like_old_code(client, order):
    booking = hold(client, order)
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "USER1", "paymentMethod": "MOMO"})
    assert is_error(r, 403, "FORBIDDEN")


def test_pay_paid_order_is_409_already_paid(client, order):
    booking = client.post("/api/booking", json=order()).json()["data"]
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "MOMO"})
    assert is_error(r, 409, "ALREADY_PAID")


def test_pay_cancelled_order_is_409(client, order):
    booking = hold(client, order)
    client.post(f"/api/booking/{booking['id']}/cancel", json={"username": "user1"})
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "MOMO"})
    assert is_error(r, 409, "BOOKING_CANCELLED")


def test_pay_unknown_order_is_404(client):
    r = client.post("/api/booking/99/pay", json={"username": "user1", "paymentMethod": "MOMO"})
    assert is_error(r, 404, "NOT_FOUND")


@pytest.mark.parametrize(
    "body, message",
    [
        ({"username": "user1"}, "paymentMethod là bắt buộc"),
        ({"username": "user1", "paymentMethod": "  "}, "paymentMethod là bắt buộc"),
        ({"username": "user1", "paymentMethod": 1}, "paymentMethod là bắt buộc"),
        ({"paymentMethod": "MOMO"}, "username là bắt buộc"),
        ({"username": "  ", "paymentMethod": "MOMO"}, "username là bắt buộc"),
        ({"username": 1, "paymentMethod": "MOMO"}, "username là bắt buộc"),
        ({}, "paymentMethod là bắt buộc"),
    ],
)
def test_pay_validation(client, order, body, message):
    booking = hold(client, order)
    r = client.post(f"/api/booking/{booking['id']}/pay", json=body)
    assert is_error(r, 400, "VALIDATION_ERROR")
    assert r.json()["message"] == message


def test_pay_when_payment_says_already_paid_recovers_the_transaction(client, upstreams, order):
    """Lần trả trước đã ghi PAID ở Payment nhưng Booking chưa biết."""
    booking = hold(client, order)
    upstreams.transactions.append(
        {"id": "9", "bookingId": booking["id"], "amount": 180000, "method": "MOMO", "status": "PAID", "paidAt": "x"}
    )
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "VNPAY"})
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "PAID"
    assert r.json()["data"]["payment"] == {"status": "PAID", "method": "VNPAY", "transactionId": "9"}


def test_reconcile_prefers_paid_over_newer_failed(client, upstreams, order):
    booking = hold(client, order)
    upstreams.transactions += [
        {"id": "1", "bookingId": booking["id"], "amount": 180000, "status": "PAID"},
        {"id": "2", "bookingId": booking["id"], "amount": 180000, "status": "FAILED"},
    ]
    upstreams.lose_payment_reply = True
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "MOMO"})
    assert r.json()["data"]["payment"]["transactionId"] == "1"


@pytest.mark.parametrize("amount", [1000, 179999, None, "180000", True])
def test_underpaid_transaction_does_not_settle_order(client, upstreams, order, amount):
    """Ai cũng gọi được POST /api/payment (Client tự gửi amount khi tạo link VNPAY): Payment ghi PAID 1.000 đ
    rồi trả 409 cho Booking. Đối soát phải so số tiền, không chốt đơn 180.000 đ chỉ vì status = PAID."""
    booking = hold(client, order)
    upstreams.transactions.append(
        {"id": "9", "bookingId": booking["id"], "amount": amount, "method": "MOMO", "status": "PAID", "paidAt": "x"}
    )
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "VNPAY"})
    assert is_error(r, 502, "PAYMENT_SERVICE_ERROR")
    assert "không đủ số tiền" in r.json()["message"]
    assert client.get(f"/api/booking/{booking['id']}").json()["data"]["status"] == "PENDING"
    assert upstreams.service_calls("notification") == []


def test_underpaid_paid_is_skipped_when_a_full_payment_exists(client, upstreams, order):
    booking = hold(client, order)
    upstreams.transactions += [
        {"id": "1", "bookingId": booking["id"], "amount": 180000, "status": "PAID"},
        {"id": "2", "bookingId": booking["id"], "amount": 1000, "status": "PAID"},
    ]
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "MOMO"})
    assert r.json()["data"]["status"] == "PAID"
    assert r.json()["data"]["payment"]["transactionId"] == "1"


def test_payment_received_after_hold_expired_still_settles_when_seats_are_free(client, upstreams, order):
    booking = hold(client, order)
    upstreams.on_payment = lambda body: age_booking(booking["id"], 11) or client.get("/api/booking")  # bị quét trong lúc chờ
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "MOMO"})
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "PAID"
    assert r.json()["data"]["notification"] == "SENT"


def test_payment_received_after_seats_were_resold_stays_cancelled_and_skips_notification(
    client, upstreams, order, caplog
):
    booking = hold(client, order, seats=["A1"])

    def expire_and_resell(body):
        upstreams.on_payment = None
        age_booking(booking["id"], 11)
        assert client.post("/api/booking", json=order(username="user2", seats=["A1"])).status_code == 201
        upstreams.calls.clear()

    upstreams.on_payment = expire_and_resell
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "MOMO"})
    data = r.json()["data"]
    assert data["status"] == "CANCELLED"
    assert data["payment"]["status"] == "PAID"
    assert data["notification"] == "SKIPPED"  # không báo "đặt vé thành công" cho đơn đã mất ghế
    assert upstreams.service_calls("notification") == []
    assert "cần hoàn tiền thủ công" in caplog.text


def test_parallel_pay_notifies_only_once(client, upstreams, order, caplog):
    """Yêu cầu thứ hai thấy đơn đã PAID sau khi chờ Payment: không gửi thông báo lần hai, không báo hoàn tiền."""
    booking = hold(client, order)

    def other_request_settles_first(body):
        upstreams.on_payment = None
        conn = sqlite3.connect(config.DB_PATH)
        conn.execute("UPDATE bookings SET status = 'PAID' WHERE id = ?", (booking["id"],))
        conn.commit()
        conn.close()

    upstreams.on_payment = other_request_settles_first
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "MOMO"})
    assert r.json()["data"]["status"] == "PAID"
    assert r.json()["data"]["notification"] == "SKIPPED"
    assert upstreams.service_calls("notification") == []
    assert "cần hoàn tiền" not in caplog.text


# ------------------------------------------------------------------ hủy
def test_cancel_releases_seats(client, upstreams, order):
    booking = hold(client, order)
    calls_before = len(upstreams.calls)
    r = client.post(f"/api/booking/{booking['id']}/cancel", json={"username": "user1"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "CANCELLED"
    assert data["expiresAt"] is None
    assert data["payment"] is None
    assert data["notification"] == "SKIPPED"
    assert seats_of(client) == []
    assert len(upstreams.calls) == calls_before  # hủy không gọi service nào


def test_cancel_twice_returns_current_state(client, order):
    booking = hold(client, order)
    path = f"/api/booking/{booking['id']}/cancel"
    client.post(path, json={"username": "user1"})
    r = client.post(path, json={"username": "user1"})
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "CANCELLED"


def test_cancel_paid_is_409(client, order):
    booking = client.post("/api/booking", json=order()).json()["data"]
    r = client.post(f"/api/booking/{booking['id']}/cancel", json={"username": "user1"})
    assert is_error(r, 409, "PAID_NOT_CANCELLABLE")


def test_cancel_by_someone_else_is_403(client, order):
    booking = hold(client, order)
    r = client.post(f"/api/booking/{booking['id']}/cancel", json={"username": "user2"})
    assert is_error(r, 403, "FORBIDDEN")
    assert rows()[0]["status"] == "PENDING"


def test_cancel_unknown_order_is_404(client):
    assert is_error(client.post("/api/booking/99/cancel", json={"username": "user1"}), 404, "NOT_FOUND")


def test_cancel_without_username_is_400(client, order):
    booking = hold(client, order)
    assert is_error(client.post(f"/api/booking/{booking['id']}/cancel", json={}), 400, "VALIDATION_ERROR")


# ------------------------------------------------------------------ đổi ghế (PUT)
def test_update_changes_seats_and_recomputes_price(client, upstreams, order):
    booking = hold(client, order)
    calls_before = len(upstreams.calls)
    r = client.put(f"/api/booking/{booking['id']}", json={"username": "user1", "seats": ["a3", "A4", "A5"]})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["seats"] == ["A3", "A4", "A5"]
    assert data["totalPrice"] == 270000  # đơn giá cũ 90000 x 3 ghế
    assert data["status"] == "PENDING"
    assert data["expiresAt"] == booking["expiresAt"]  # đổi ghế không kéo dài hạn giữ
    assert "payment" not in data
    assert seats_of(client) == ["A3", "A4", "A5"]
    assert len(upstreams.calls) == calls_before  # không gọi service nào


def test_update_may_keep_some_of_its_own_seats(client, order):
    booking = hold(client, order)
    r = client.put(f"/api/booking/{booking['id']}", json={"username": "user1", "seats": ["A2", "A3"]})
    assert r.json()["data"]["seats"] == ["A2", "A3"]


def test_update_to_seat_of_other_order_is_409_and_nothing_changes(client, order):
    hold(client, order, username="user2", seats=["B1"])
    booking = hold(client, order)
    r = client.put(f"/api/booking/{booking['id']}", json={"username": "user1", "seats": ["A1", "B1"]})
    assert is_error(r, 409, "SEAT_TAKEN")
    assert "B1" in r.json()["message"]
    assert rows("SELECT seats, total_price FROM bookings WHERE id = ?", booking["id"])[0]["seats"] == "A1,A2"


def test_update_paid_order_is_409(client, order):
    booking = client.post("/api/booking", json=order()).json()["data"]
    r = client.put(f"/api/booking/{booking['id']}", json={"username": "user1", "seats": ["A3"]})
    assert is_error(r, 409, "ALREADY_PAID")


@pytest.mark.parametrize("make_cancelled", [
    lambda c, b: c.post(f"/api/booking/{b}/cancel", json={"username": "user1"}),
    lambda _, b: age_booking(b, 11),
])
def test_update_cancelled_or_expired_order_is_409(client, order, make_cancelled):
    booking = hold(client, order)
    make_cancelled(client, booking["id"])
    r = client.put(f"/api/booking/{booking['id']}", json={"username": "user1", "seats": ["A3"]})
    assert is_error(r, 409, "BOOKING_CANCELLED")


def test_update_by_someone_else_is_403(client, order):
    booking = hold(client, order)
    r = client.put(f"/api/booking/{booking['id']}", json={"username": "user2", "seats": ["A3"]})
    assert is_error(r, 403, "FORBIDDEN")
    assert rows()[0]["seats"] == "A1,A2"


def test_update_unknown_order_is_404(client):
    assert is_error(client.put("/api/booking/99", json={"username": "user1", "seats": ["A1"]}), 404, "NOT_FOUND")


@pytest.mark.parametrize(
    "body, message",
    [
        ({"seats": ["A1"]}, "username là bắt buộc"),
        ({"username": "user1"}, 'seats là bắt buộc, ví dụ ["A1","A2"]'),
        ({"username": "user1", "seats": []}, "Mỗi đơn đặt từ 1 đến 10 ghế"),
        ({"username": "user1", "seats": ["A1", "a1"]}, "Danh sách ghế bị trùng"),
        ({"username": "user1", "seats": ["ZZ"]}, "Mã ghế không hợp lệ (ví dụ A1, B12)"),
    ],
)
def test_update_validation(client, order, body, message):
    booking = hold(client, order)
    r = client.put(f"/api/booking/{booking['id']}", json=body)
    assert is_error(r, 400, "VALIDATION_ERROR")
    assert r.json()["message"] == message


def test_update_with_malformed_body_is_400(client, order):
    booking = hold(client, order)
    r = client.put(f"/api/booking/{booking['id']}", content=b"{not json")
    assert is_error(r, 400, "VALIDATION_ERROR")


# ------------------------------------------------------------------ xóa (DELETE)
def test_delete_removes_order_and_frees_seats(client, upstreams, order):
    booking = hold(client, order)
    calls_before = len(upstreams.calls)
    r = client.delete(f"/api/booking/{booking['id']}?username=user1")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == booking["id"]
    assert r.json()["data"]["seats"] == ["A1", "A2"]
    assert rows() == []
    assert is_error(client.get(f"/api/booking/{booking['id']}"), 404, "NOT_FOUND")
    assert seats_of(client) == []
    assert len(upstreams.calls) == calls_before


def test_delete_paid_order_is_allowed(client, order):
    booking = client.post("/api/booking", json=order()).json()["data"]
    r = client.delete(f"/api/booking/{booking['id']}?username=user1")
    assert r.json()["data"]["status"] == "PAID"
    assert rows() == []


def test_deleted_id_is_never_reused(client, order):
    """Payment/Notification vẫn giữ id cũ: đơn mới không được trùng id đã xóa."""
    hold(client, order, seats=["A1"])
    second = hold(client, order, seats=["A2"])
    client.delete(f"/api/booking/{second['id']}?username=user1")
    assert hold(client, order, seats=["A3"])["id"] == second["id"] + 1


def test_delete_by_someone_else_is_403_and_keeps_order(client, order):
    booking = hold(client, order)
    assert is_error(client.delete(f"/api/booking/{booking['id']}?username=user2"), 403, "FORBIDDEN")
    assert len(rows()) == 1


def test_delete_unknown_order_is_404(client):
    assert is_error(client.delete("/api/booking/99?username=user1"), 404, "NOT_FOUND")


@pytest.mark.parametrize("query", ["", "?username=", "?username=%20"])
def test_delete_without_username_is_400(client, order, query):
    booking = hold(client, order)
    r = client.delete(f"/api/booking/{booking['id']}{query}")
    assert is_error(r, 400, "VALIDATION_ERROR")
    assert len(rows()) == 1


# ------------------------------------------------------------------ hết hạn giữ ghế
@pytest.mark.parametrize(
    "read",
    [
        lambda c, b: c.get(f"/api/booking/{b}").json()["data"]["status"],
        lambda c, b: c.get("/api/booking").json()["data"][0]["status"],
        lambda c, b: c.post(f"/api/booking/{b}/cancel", json={"username": "user1"}).json()["data"]["status"],
    ],
)
def test_expired_hold_is_cancelled_on_read(client, order, read):
    booking = hold(client, order)
    age_booking(booking["id"], 11)
    assert read(client, booking["id"]) == "CANCELLED"


def test_expired_hold_releases_seats_for_seat_map_and_availability(client, order):
    booking = hold(client, order)
    age_booking(booking["id"], 11)
    assert seats_of(client) == []
    assert client.get("/api/booking/availability?showtimeIds=1").json()["data"][0]["taken"] == 0


def test_expired_seat_can_be_booked_immediately(client, order):
    booking = hold(client, order)
    age_booking(booking["id"], 11)
    assert client.post("/api/booking", json=order(username="user2")).status_code == 201


def test_expired_hold_cannot_be_paid(client, order):
    booking = hold(client, order)
    age_booking(booking["id"], 11)
    r = client.post(f"/api/booking/{booking['id']}/pay", json={"username": "user1", "paymentMethod": "MOMO"})
    assert is_error(r, 409, "BOOKING_CANCELLED")


def test_hold_within_limit_is_kept(client, order):
    booking = hold(client, order)
    age_booking(booking["id"], 9)
    assert client.get(f"/api/booking/{booking['id']}").json()["data"]["status"] == "PENDING"


def test_seeded_old_pending_order_expires(seeded_client):
    assert seeded_client.get("/api/booking/3").json()["data"]["status"] == "CANCELLED"


def test_paid_order_never_expires(client, order):
    booking = client.post("/api/booking", json=order()).json()["data"]
    age_booking(booking["id"], 1000)
    assert client.get(f"/api/booking/{booking['id']}").json()["data"]["status"] == "PAID"
