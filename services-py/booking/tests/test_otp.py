"""OTP thanh toán: Booking điều phối Payment (sinh mã) -> Notification (gửi email) -> /pay kèm mã."""
import json

import pytest

from app.core import config
from tests.test_booking_flow import hold, is_error, rows


@pytest.fixture
def otp_on(monkeypatch, upstreams):
    monkeypatch.setattr(config, "OTP_REQUIRED", True)
    upstreams.otp_required = True
    upstreams.emails["user1"] = "user1@cinema.local"
    return upstreams


def request_otp(client, booking_id, username="user1"):
    return client.post(f"/api/booking/{booking_id}/otp", json={"username": username})


def pay(client, booking_id, otp=None, username="user1"):
    body = {"username": username, "paymentMethod": "MOMO"}
    if otp is not None:
        body["otp"] = otp
    return client.post(f"/api/booking/{booking_id}/pay", json=body)


def test_request_otp_asks_payment_then_notification_without_leaking_code(client, otp_on, order):
    booking = hold(client, order)
    r = request_otp(client, booking["id"])
    assert r.status_code == 200
    d = r.json()["data"]
    assert d == {"bookingId": booking["id"], "channel": "EMAIL", "maskedEmail": "us***@cinema.local",
                 "expiresInSeconds": 300, "delivery": "SIMULATED"}
    assert "123456" not in r.text and "devOtp" not in d  # OTP_DEBUG tắt: không trả mã
    mail = json.loads(otp_on.service_calls("notification")[-1].content)
    assert mail == {"username": "user1", "bookingId": booking["id"], "email": "user1@cinema.local",
                    "otp": "123456", "ttlSeconds": 300}
    assert otp_on.service_calls("notification")[-1].url.path == "/api/notify/otp"


def test_dev_otp_returned_only_in_debug_mode(client, otp_on, order, monkeypatch):
    monkeypatch.setattr(config, "OTP_DEBUG", True)
    booking = hold(client, order)
    assert request_otp(client, booking["id"]).json()["data"]["devOtp"] == "123456"


def test_full_flow_pay_with_correct_otp(client, otp_on, order):
    booking = hold(client, order)
    request_otp(client, booking["id"])
    r = pay(client, booking["id"], "123456")
    assert r.status_code == 200 and r.json()["data"]["status"] == "PAID"
    charge = [c for c in otp_on.service_calls("payment") if c.url.path == "/api/payment"][-1]
    assert json.loads(charge.content)["otp"] == "123456"
    assert [dict(x)["status"] for x in rows()] == ["PAID"]


def test_pay_without_otp_keeps_order_pending(client, otp_on, order):
    booking = hold(client, order)
    r = pay(client, booking["id"])
    assert is_error(r, 400, "OTP_REQUIRED")
    assert [dict(x)["status"] for x in rows()] == ["PENDING"]  # không hủy đơn, ghế vẫn giữ


def test_wrong_otp_keeps_order_pending_and_can_retry(client, otp_on, order):
    booking = hold(client, order)
    request_otp(client, booking["id"])
    assert is_error(pay(client, booking["id"], "000000"), 400, "OTP_INVALID")
    assert [dict(x)["status"] for x in rows()] == ["PENDING"]
    assert pay(client, booking["id"], "123456").json()["data"]["status"] == "PAID"


def test_otp_may_be_sent_as_number(client, otp_on, order):
    booking = hold(client, order)
    request_otp(client, booking["id"])
    assert pay(client, booking["id"], 123456).status_code == 200


def test_pay_now_is_refused_when_otp_required_and_nothing_saved(client, otp_on, order):
    assert is_error(client.post("/api/booking", json=order()), 400, "OTP_REQUIRED")
    assert rows() == []


def test_unknown_user_or_closed_showtime_reported_before_otp_requirement(client, otp_on, order):
    """Dữ liệu sai báo đúng lỗi 404/400 của nó, không bị che bởi OTP_REQUIRED."""
    assert is_error(client.post("/api/booking", json=order(username="khong_co")), 404, "USER_NOT_FOUND")
    assert is_error(client.post("/api/booking", json=order(showtimeId=3)), 400, "SHOWTIME_CLOSED")


def test_pay_now_still_works_when_otp_not_required(client, order):
    assert client.post("/api/booking", json=order()).status_code == 201


def test_otp_resend_too_soon_is_429(client, otp_on, order):
    booking = hold(client, order)
    otp_on.otp_too_soon = True
    assert is_error(request_otp(client, booking["id"]), 429, "OTP_TOO_SOON")


def test_user_without_email_gets_400(client, otp_on, order):
    otp_on.emails.clear()
    booking = hold(client, order)
    assert is_error(request_otp(client, booking["id"]), 400, "EMAIL_REQUIRED")
    assert otp_on.service_calls("notification") == []


def test_email_delivery_failure_is_reported(client, otp_on, order):
    booking = hold(client, order)
    otp_on.broken_otp_mail = True
    assert is_error(request_otp(client, booking["id"]), 502, "NOTIFICATION_SERVICE_ERROR")


def test_notification_down_is_503(client, otp_on, order):
    booking = hold(client, order)
    otp_on.down.add("notification")
    assert is_error(request_otp(client, booking["id"]), 503, "NOTIFICATION_SERVICE_UNAVAILABLE")


def test_payment_down_is_503(client, otp_on, order):
    booking = hold(client, order)
    otp_on.down.add("payment")
    assert is_error(request_otp(client, booking["id"]), 503, "PAYMENT_SERVICE_UNAVAILABLE")


def test_only_owner_can_request_otp(client, otp_on, order):
    booking = hold(client, order)
    assert is_error(request_otp(client, booking["id"], username="user2"), 403, "FORBIDDEN")
    assert otp_on.service_calls("payment") == []


@pytest.mark.parametrize("status_fn,code,http", [
    (lambda c, o, b: pay(c, b["id"], "123456"), "ALREADY_PAID", 409),
    (lambda c, o, b: c.post(f"/api/booking/{b['id']}/cancel", json={"username": "user1"}), "BOOKING_CANCELLED", 409),
])
def test_cannot_request_otp_for_paid_or_cancelled(client, otp_on, order, status_fn, code, http):
    booking = hold(client, order)
    request_otp(client, booking["id"])
    status_fn(client, order, booking)
    assert is_error(request_otp(client, booking["id"]), http, code)


def test_unknown_order_is_404_and_bad_body_400(client, otp_on):
    assert request_otp(client, 999).status_code == 404
    assert client.post("/api/booking/1/otp", json={}).status_code == 400


def test_notification_email_included_in_confirmation(client, upstreams, order):
    """Có email của người dùng thì xác nhận đặt vé gửi kèm để Notification gửi email thật."""
    upstreams.emails["user1"] = "user1@cinema.local"
    client.post("/api/booking", json=order())
    sent = json.loads(upstreams.service_calls("notification")[0].content)
    assert sent == {"username": "user1", "bookingId": 1, "channel": "EMAIL", "email": "user1@cinema.local"}


def test_confirmation_after_pay_looks_up_email(client, upstreams, order):
    upstreams.emails["user1"] = "user1@cinema.local"
    booking = hold(client, order)
    pay(client, booking["id"])
    sent = json.loads(upstreams.service_calls("notification")[-1].content)
    assert sent["email"] == "user1@cinema.local"
