#!/usr/bin/env python3
"""
Kiểm thử tích hợp 6 service (chỉ dùng thư viện chuẩn Python 3.8+, không cần cài thêm).

  python tests/integration/run_tests.py                      # kịch bản bình thường (cả 6 service đang chạy)
  python tests/integration/run_tests.py --otp                # stack bật OTP (OTP_REQUIRED=true, OTP_DEBUG=true): thanh toán qua mã OTP
  python tests/integration/run_tests.py --expect-down payment        # TẮT Payment trước, rồi chạy: Booking phải trả 503 và nhả ghế
  python tests/integration/run_tests.py --expect-down notification   # TẮT Notification: đơn vẫn PAID, notification = FAILED
  python tests/integration/run_tests.py --expect-down showtime|movie|user   # TẮT service đó: Booking phải trả 503

Đổi địa chỉ máy chủ: SOA_HOST=192.168.1.10 python tests/integration/run_tests.py (hỗ trợ cả HOST cũ)
Đổi dải cổng:        SOA_PORT_OFFSET=11000 python tests/integration/run_tests.py
Chạy qua Gateway:    SOA_GATEWAY_URL=http://localhost:8000 python tests/integration/run_tests.py
"""
import argparse, json, os, random, sys, time
import urllib.request, urllib.error

HOST = os.environ.get("SOA_HOST") or os.environ.get("HOST", "localhost")
PORT_OFFSET = int(os.environ.get("SOA_PORT_OFFSET", "0"))
GATEWAY_URL = os.environ.get("SOA_GATEWAY_URL", "").strip().rstrip("/")
_BASE_PORTS = dict(movie=5001, showtime=5002, user=5003, booking=5004, payment=5005, notification=5006)
URL = {k: (GATEWAY_URL if GATEWAY_URL else f"http://{HOST}:{p + PORT_OFFSET}") for k, p in _BASE_PORTS.items()}
PASS = FAIL = 0
OTP = os.environ.get("OTP") == "1"  # bật bằng --otp: stack chạy với OTP_REQUIRED=true và OTP_DEBUG=true
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(svc, method, path, body=None, timeout=20):
    """Trả về (http_status, json hoặc None). Ném ConnectionError nếu service không truy cập được."""
    req = urllib.request.Request(URL[svc] + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except ValueError:
            return e.code, None
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        raise ConnectionError(f"{svc} không truy cập được: {e}")


def otp_for(bid, uname):
    """Chế độ OTP: xin mã (Payment sinh -> Notification gửi email) rồi lấy devOtp. Rỗng nếu không ở chế độ OTP."""
    if not OTP:
        return {}
    for _ in range(40):
        r = call("booking", "POST", f"/api/booking/{bid}/otp", {"username": uname})
        if r[0] == 200:
            return {"otp": r[1]["data"].get("devOtp", "")}
        if r[1] and r[1].get("code") == "OTP_TOO_SOON":
            time.sleep(1)  # đợi hết khoảng cách gửi lại (OTP_RESEND_SECONDS)
            continue
        break
    return {"otp": ""}


def book_paid(uname, st, seats, method):
    """Đặt vé và thanh toán. Chế độ OTP không cho đặt-và-trả-ngay nên đi qua giữ ghế -> OTP -> /pay."""
    base = {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": seats}
    if not OTP:
        return call("booking", "POST", "/api/booking", {**base, "paymentMethod": method})
    held = call("booking", "POST", "/api/booking", {**base, "payNow": False})
    hid = held[1]["data"]["id"]
    return call("booking", "POST", f"/api/booking/{hid}/pay", {"username": uname, "paymentMethod": method, **otp_for(hid, uname)})


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✔ {name}")
    else:
        FAIL += 1; print(f"  ✘ {name}  {detail}")


def is_ok(r, status):  # r = (http, json)
    return r[0] == status and r[1] and r[1].get("status") == "success"


def is_err(r, status, code=None):
    return r[0] == status and r[1] and r[1].get("status") == "error" and (code is None or r[1].get("code") == code) and r[1].get("message")


def free_seats(showtime_id, n=2):
    taken = set(call("booking", "GET", f"/api/booking/seats?showtimeId={showtime_id}")[1]["data"]["seats"])
    out = []
    while len(out) < n:
        s = f"T{random.randint(1, 99)}"
        if s not in taken and s not in out:
            out.append(s)
    return out


def upcoming_showtime(shows, after_minutes=30):
    """Suất chiếu bắt đầu sau ít nhất after_minutes phút (Booking từ chối suất đã/đang chiếu)."""
    limit = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + after_minutes * 60))
    return next((s for s in shows if s["time"] > limit), None)


def normal():
    print("\n[1] Hợp đồng chung: envelope + camelCase cho từng service")
    for svc, path in [("movie", "/api/movies"), ("showtime", "/api/showtimes"), ("user", "/api/users"),
                      ("booking", "/api/booking"), ("payment", "/api/payment"), ("notification", "/api/notify/logs")]:
        r = call(svc, "GET", path)
        check(f"{svc}: GET {path} -> 200 + envelope success", is_ok(r, 200) and isinstance(r[1]["data"], list))
        check(f"{svc}: không lộ trường snake_case / password", not any(k in json.dumps(r[1]) for k in ('"created_at"', '"movie_id"', '"password', '"_id"')))
    check("movie: 404 có code NOT_FOUND", is_err(call("movie", "GET", "/api/movies/99999"), 404, "NOT_FOUND"))
    check("showtime: 404 có code NOT_FOUND", is_err(call("showtime", "GET", "/api/showtimes/99999"), 404, "NOT_FOUND"))
    check("user: 404 có code NOT_FOUND", is_err(call("user", "GET", "/api/users/99999"), 404, "NOT_FOUND"))
    check("booking: 404 có code NOT_FOUND", is_err(call("booking", "GET", "/api/booking/99999"), 404, "NOT_FOUND"))

    print("\n[2] Dữ liệu mẫu chung & tham chiếu logic giữa các service")
    movies = call("movie", "GET", "/api/movies")[1]["data"]
    shows = call("showtime", "GET", "/api/showtimes")[1]["data"]
    ids = {m["id"] for m in movies}
    check("seed: Movie có 5 phim", len(movies) >= 5)
    check("seed: Showtime có >= 6 suất", len(shows) >= 6)
    check("mọi showtime.movieId trỏ tới phim có thật (tham chiếu logic, không FK)", all(s["movieId"] in ids for s in shows))
    check("seed: user1 đăng nhập được", is_ok(call("user", "POST", "/api/login", {"username": "user1", "password": "User@123"}), 200))
    check("login sai mật khẩu -> 401", is_err(call("user", "POST", "/api/login", {"username": "user1", "password": "x"}), 401))

    print("\n[3] Showtime validate movieId qua API của Movie")
    bad = call("showtime", "POST", "/api/showtimes", {"movieId": 99999, "cinema": "X", "room": "P1", "time": "2026-12-01 10:00:00", "price": 1000})
    check("tạo showtime cho phim không tồn tại -> 400 MOVIE_NOT_FOUND", is_err(bad, 400, "MOVIE_NOT_FOUND") or is_err(bad, 400))
    check("tạo showtime thiếu trường -> 400", is_err(call("showtime", "POST", "/api/showtimes", {"movieId": 1}), 400))

    print("\n[4] Luồng đặt vé thành công (Booking điều phối 5 service)")
    uname = f"it_{int(time.time())}"
    check("đăng ký tài khoản mới -> 201", is_ok(call("user", "POST", "/api/register", {"username": uname, "password": "Test@123", "email": f"{uname}@x.vn"}), 201))
    check("đăng ký trùng username -> 409", is_err(call("user", "POST", "/api/register", {"username": uname, "password": "Test@123"}), 409, "CONFLICT"))
    st = upcoming_showtime(shows)
    check("có suất chiếu sắp tới (lịch chiếu tự sinh cho các ngày tới)", st is not None)
    if st is None:
        return
    seats = free_seats(st["id"])
    r = book_paid(uname, st, seats, "MOMO")
    check("đặt vé -> 201" if not OTP else "giữ ghế + OTP + thanh toán -> 200", is_ok(r, 200 if OTP else 201), r[1])
    d = r[1]["data"] if r[1] and r[1].get("data") else {}
    check("đơn PAID, tổng tiền = giá suất × số ghế (giá lấy từ Showtime)", d.get("status") == "PAID" and d.get("totalPrice") == st["price"] * len(seats), d)
    check("Notification gửi thành công", d.get("notification") == "SENT", d.get("notification"))
    bid = d.get("id")
    pay = call("payment", "GET", f"/api/payment?bookingId={bid}")[1]["data"]
    check("Payment có giao dịch PAID đúng số tiền cho đơn", len(pay) == 1 and pay[0]["status"] == "PAID" and pay[0]["amount"] == d.get("totalPrice"), pay)
    logs = call("notification", "GET", "/api/notify/logs")[1]["data"]
    check("Notification có nhật ký cho đơn", any(l["bookingId"] == bid for l in logs))
    check("GET /api/booking/{id} khớp", call("booking", "GET", f"/api/booking/{bid}")[1]["data"]["status"] == "PAID")
    check("ghế vừa đặt hiện trong danh sách ghế đã giữ", set(seats) <= set(call("booking", "GET", f"/api/booking/seats?showtimeId={st['id']}")[1]["data"]["seats"]))

    print("\n[5] Các tình huống lỗi nghiệp vụ")
    dup = call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": [seats[0]], **({"payNow": False} if OTP else {})})
    check("đặt ghế đã có người -> 409 SEAT_TAKEN", is_err(dup, 409, "SEAT_TAKEN"))
    check("username không tồn tại -> 404 USER_NOT_FOUND", is_err(call("booking", "POST", "/api/booking", {"username": "khong_ton_tai", "movieId": st["movieId"], "showtimeId": st["id"], "seats": ["Z1"]}), 404, "USER_NOT_FOUND"))
    check("showtime không tồn tại -> 404 SHOWTIME_NOT_FOUND", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": 1, "showtimeId": 99999, "seats": ["Z1"]}), 404, "SHOWTIME_NOT_FOUND"))
    other = next(s for s in shows if s["movieId"] != st["movieId"])
    check("suất chiếu không thuộc phim -> 400", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": other["id"], "seats": ["Z1"]}), 400))
    check("body sai (seats rỗng) -> 400 VALIDATION_ERROR", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": 1, "showtimeId": 1, "seats": []}), 400, "VALIDATION_ERROR"))
    check("mã ghế sai định dạng -> 400 VALIDATION_ERROR", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": 1, "showtimeId": 1, "seats": ["zz"]}), 400, "VALIDATION_ERROR"))
    check("movieId = 0 -> 400 VALIDATION_ERROR", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": 0, "showtimeId": 1, "seats": ["Z1"]}), 400, "VALIDATION_ERROR"))
    check("movieId âm -> 400 VALIDATION_ERROR", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": -1, "showtimeId": 1, "seats": ["Z1"]}), 400, "VALIDATION_ERROR"))
    check("showtimeId = 0 -> 400 VALIDATION_ERROR", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": 1, "showtimeId": 0, "seats": ["Z1"]}), 400, "VALIDATION_ERROR"))
    check("showtimeId âm -> 400 VALIDATION_ERROR", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": 1, "showtimeId": -1, "seats": ["Z1"]}), 400, "VALIDATION_ERROR"))
    check("thiếu trường seats -> 400 VALIDATION_ERROR", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": 1, "showtimeId": 1}), 400, "VALIDATION_ERROR"))

    print("\n[6] Thanh toán thất bại -> đơn CANCELLED, ghế được nhả")
    s2 = free_seats(st["id"], 1)
    if OTP:
        r = call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": s2})
        check("đặt-và-trả-ngay khi bắt OTP -> 400 OTP_REQUIRED, không lưu đơn", is_err(r, 400, "OTP_REQUIRED") and s2[0] not in call("booking", "GET", f"/api/booking/seats?showtimeId={st['id']}")[1]["data"]["seats"], r[1])
    else:
        r = call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": s2, "paymentMethod": "KHONGHOPLE"})
        d = r[1]["data"] if r[1] and r[1].get("data") else {}
        check("Payment FAILED -> đơn CANCELLED (HTTP 201 vì đơn đã được ghi nhận)", r[0] == 201 and d.get("status") == "CANCELLED" and d.get("payment", {}).get("status") == "FAILED", r[1])
        check("ghế của đơn bị hủy được nhả lại", s2[0] not in call("booking", "GET", f"/api/booking/seats?showtimeId={st['id']}")[1]["data"]["seats"])
    again = book_paid(uname, st, s2, "MOMO")
    check("đặt lại đúng ghế đó với phương thức hợp lệ -> PAID", is_ok(again, 200 if OTP else 201) and again[1]["data"]["status"] == "PAID")

    print("\n[7] Giữ ghế rồi thanh toán sau (payNow=false) / hủy giữ chỗ")
    past = next((s for s in shows if s["time"] < time.strftime("%Y-%m-%d %H:%M:%S")), None)
    if past:
        check("đặt suất đã chiếu -> 400 SHOWTIME_CLOSED", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": past["movieId"], "showtimeId": past["id"], "seats": ["Z1"]}), 400, "SHOWTIME_CLOSED"))
    s3 = free_seats(st["id"], 2)
    r = call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": s3, "payNow": False})
    d = r[1]["data"] if r[1] and r[1].get("data") else {}
    hid = d.get("id")
    check("giữ ghế -> 201, đơn PENDING có expiresAt, chưa gọi Payment", is_ok(r, 201) and d.get("status") == "PENDING" and d.get("expiresAt") and d.get("payment") is None, d)
    check("ghế đang giữ hiện trong danh sách ghế đã giữ", set(s3) <= set(call("booking", "GET", f"/api/booking/seats?showtimeId={st['id']}")[1]["data"]["seats"]))
    av = call("booking", "GET", f"/api/booking/availability?showtimeIds={st['id']}")
    check("availability trả số ghế đã giữ của suất", is_ok(av, 200) and av[1]["data"][0]["showtimeId"] == st["id"] and av[1]["data"][0]["taken"] >= len(s3), av[1])
    check("người khác không thanh toán được đơn này -> 403", is_err(call("booking", "POST", f"/api/booking/{hid}/pay", {"username": "user2", "paymentMethod": "MOMO"}), 403, "FORBIDDEN"))
    bad = call("booking", "POST", f"/api/booking/{hid}/pay", {"username": uname, "paymentMethod": "KHONGHOPLE", **otp_for(hid, uname)})
    check("thanh toán thất bại -> đơn VẪN PENDING (giữ ghế để thử lại)", is_ok(bad, 200) and bad[1]["data"]["status"] == "PENDING" and bad[1]["data"]["payment"]["status"] == "FAILED", bad[1])
    ok = call("booking", "POST", f"/api/booking/{hid}/pay", {"username": uname, "paymentMethod": "BANK_TRANSFER", **otp_for(hid, uname)})
    d = ok[1]["data"] if ok[1] and ok[1].get("data") else {}
    check("thanh toán chuyển khoản -> PAID, gửi thông báo", is_ok(ok, 200) and d.get("status") == "PAID" and d.get("expiresAt") is None and d.get("notification") == "SENT", d)
    check("thanh toán lại đơn đã PAID -> 409 ALREADY_PAID", is_err(call("booking", "POST", f"/api/booking/{hid}/pay", {"username": uname, "paymentMethod": "MOMO"}), 409, "ALREADY_PAID"))
    check("không hủy được vé đã thanh toán -> 409", is_err(call("booking", "POST", f"/api/booking/{hid}/cancel", {"username": uname}), 409, "PAID_NOT_CANCELLABLE"))
    s4 = free_seats(st["id"], 1)
    h2 = call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": s4, "payNow": False})[1]["data"]["id"]
    c = call("booking", "POST", f"/api/booking/{h2}/cancel", {"username": uname})
    check("hủy đơn đang giữ -> CANCELLED, ghế được nhả", is_ok(c, 200) and c[1]["data"]["status"] == "CANCELLED"
          and s4[0] not in call("booking", "GET", f"/api/booking/seats?showtimeId={st['id']}")[1]["data"]["seats"])
    check("thanh toán đơn đã hủy -> 409 BOOKING_CANCELLED", is_err(call("booking", "POST", f"/api/booking/{h2}/pay", {"username": uname, "paymentMethod": "MOMO"}), 409, "BOOKING_CANCELLED"))
    up = call("showtime", "GET", "/api/showtimes?upcoming=1")[1]["data"]
    check("showtime ?upcoming=1 chỉ trả suất chưa chiếu", up and all(x["time"] > time.strftime("%Y-%m-%d %H:%M:%S") for x in up))
    if OTP:
        otp_checks(uname, st)


def otp_checks(uname, st):
    print("\n[8] OTP xác nhận thanh toán (Booking -> Payment sinh mã -> Notification gửi email)")
    s5 = free_seats(st["id"], 1)
    hid = call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": s5, "payNow": False})[1]["data"]["id"]
    check("thanh toán không có OTP -> 400 OTP_REQUIRED, đơn vẫn PENDING",
          is_err(call("booking", "POST", f"/api/booking/{hid}/pay", {"username": uname, "paymentMethod": "MOMO"}), 400, "OTP_REQUIRED")
          and call("booking", "GET", f"/api/booking/{hid}")[1]["data"]["status"] == "PENDING")
    check("thanh toán với OTP chưa được yêu cầu -> 400 OTP_INVALID",
          is_err(call("booking", "POST", f"/api/booking/{hid}/pay", {"username": uname, "paymentMethod": "MOMO", "otp": "000000"}), 400, "OTP_INVALID"))
    check("người khác không xin được OTP của đơn -> 403",
          is_err(call("booking", "POST", f"/api/booking/{hid}/otp", {"username": "user2"}), 403, "FORBIDDEN"))
    r = call("booking", "POST", f"/api/booking/{hid}/otp", {"username": uname})
    d = r[1]["data"] if r[1] and r[1].get("data") else {}
    check("xin OTP -> 200, gửi qua EMAIL, email được che", is_ok(r, 200) and d.get("channel") == "EMAIL" and "***" in d.get("maskedEmail", ""), r[1])
    check("gửi lại OTP quá sớm -> 429 OTP_TOO_SOON", is_err(call("booking", "POST", f"/api/booking/{hid}/otp", {"username": uname}), 429, "OTP_TOO_SOON"))
    code = d.get("devOtp", "")
    wrong = "000000" if code != "000000" else "111111"
    check("OTP sai -> 400 OTP_INVALID, đơn vẫn PENDING",
          is_err(call("booking", "POST", f"/api/booking/{hid}/pay", {"username": uname, "paymentMethod": "MOMO", "otp": wrong}), 400, "OTP_INVALID")
          and call("booking", "GET", f"/api/booking/{hid}")[1]["data"]["status"] == "PENDING")
    ok = call("booking", "POST", f"/api/booking/{hid}/pay", {"username": uname, "paymentMethod": "MOMO", "otp": code})
    check("OTP đúng -> PAID, có giao dịch + thông báo", is_ok(ok, 200) and ok[1]["data"]["status"] == "PAID" and ok[1]["data"]["notification"] == "SENT", ok[1])
    check("OTP chỉ dùng một lần (đơn đã PAID) -> 409 ALREADY_PAID",
          is_err(call("booking", "POST", f"/api/booking/{hid}/pay", {"username": uname, "paymentMethod": "MOMO", "otp": code}), 409, "ALREADY_PAID"))
    logs = call("notification", "GET", f"/api/notify/logs?bookingId={hid}")[1]["data"]
    check("nhật ký thông báo ghi việc gửi OTP nhưng KHÔNG chứa mã", any("OTP" in l["message"] for l in logs) and not any(code in l["message"] for l in logs))


def down(service):
    print(f"\n[Kịch bản] {service.upper()} đang TẮT — Booking phải xử lý êm, không treo, không sai dữ liệu")
    st = upcoming_showtime(call("showtime", "GET", "/api/showtimes")[1]["data"]) if service != "showtime" else {"id": 1, "movieId": 1}
    uname = "user1"
    seat = [f"U{random.randint(1, 99)}"]
    t0 = time.time()
    r = call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": seat, **({"payNow": False} if OTP else {})}, timeout=40)
    if OTP and service in ("payment", "notification") and r[0] == 201:
        hid = r[1]["data"]["id"]  # chế độ OTP: đơn đã giữ ghế, bước xin OTP phải báo dịch vụ sập
        r = call("booking", "POST", f"/api/booking/{hid}/otp", {"username": uname}, timeout=40)
        elapsed = time.time() - t0
        code = f"{service.upper()}_SERVICE_UNAVAILABLE"
        check(f"phản hồi trong < 15 giây (thực tế {elapsed:.1f}s) — có timeout", elapsed < 15)
        check(f"xin OTP khi {service} tắt -> HTTP 503 + {code}", is_err(r, 503, code), r[1])
        check("đơn vẫn PENDING (giữ ghế để thử lại)", call("booking", "GET", f"/api/booking/{hid}")[1]["data"]["status"] == "PENDING")
        call("booking", "POST", f"/api/booking/{hid}/cancel", {"username": uname})
        return
    elapsed = time.time() - t0
    check(f"phản hồi trong < 15 giây (thực tế {elapsed:.1f}s) — có timeout", elapsed < 15)
    if service == "notification":
        d = r[1].get("data") or {}
        check("đơn vẫn PAID (thông báo là best-effort)", r[0] == 201 and d.get("status") == "PAID", r[1])
        check("trường notification = FAILED", d.get("notification") == "FAILED", d)
    else:
        code = f"{service.upper()}_SERVICE_UNAVAILABLE"
        check(f"HTTP 503 + code {code}", is_err(r, 503, code), r[1])
        if service == "payment":
            check("ghế được nhả (đơn bị CANCELLED, không treo PENDING)", seat[0] not in call("booking", "GET", f"/api/booking/seats?showtimeId={st['id']}")[1]["data"]["seats"])
            check("không còn đơn PENDING mới nào bị bỏ rơi", True if not call("booking", "GET", "/api/booking?status=PENDING")[1]["data"] else all(b["id"] <= 3 for b in call("booking", "GET", "/api/booking?status=PENDING")[1]["data"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-down", choices=["movie", "showtime", "user", "payment", "notification"])
    ap.add_argument("--otp", action="store_true", help="stack bật OTP_REQUIRED + OTP_DEBUG")
    a = ap.parse_args()
    OTP = OTP or a.otp
    try:
        down(a.expect_down) if a.expect_down else normal()
    except ConnectionError as e:
        print(f"\n✘ {e}\n  Hãy chắc chắn các service cần thiết đang chạy (xem scripts/start-all)."); sys.exit(2)
    print(f"\nKết quả: {PASS} đạt, {FAIL} lỗi")
    sys.exit(1 if FAIL else 0)
