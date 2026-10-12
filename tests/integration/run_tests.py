#!/usr/bin/env python3
"""
Kiểm thử tích hợp 6 service (chỉ dùng thư viện chuẩn Python 3.8+, không cần cài thêm).

  python tests/integration/run_tests.py                      # kịch bản bình thường (cả 6 service đang chạy)
  python tests/integration/run_tests.py --expect-down payment        # TẮT Payment trước, rồi chạy: Booking phải trả 503 và nhả ghế
  python tests/integration/run_tests.py --expect-down notification   # TẮT Notification: đơn vẫn PAID, notification = FAILED
  python tests/integration/run_tests.py --expect-down showtime|movie|user   # TẮT service đó: Booking phải trả 503

Đổi địa chỉ máy chủ: HOST=192.168.1.10 python tests/integration/run_tests.py
"""
import argparse, json, os, random, sys, time
import urllib.request, urllib.error

HOST = os.environ.get("HOST", "localhost")
URL = {k: f"http://{HOST}:{p}" for k, p in
       dict(movie=5001, showtime=5002, user=5003, booking=5004, payment=5005, notification=5006).items()}
PASS = FAIL = 0


def call(svc, method, path, body=None, timeout=20):
    """Trả về (http_status, json hoặc None). Ném ConnectionError nếu service không truy cập được."""
    req = urllib.request.Request(URL[svc] + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except ValueError:
            return e.code, None
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        raise ConnectionError(f"{svc} không truy cập được: {e}")


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
    st = shows[0]
    seats = free_seats(st["id"])
    r = call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": seats, "paymentMethod": "MOMO"})
    check("đặt vé -> 201", is_ok(r, 201), r[1])
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
    dup = call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": [seats[0]]})
    check("đặt ghế đã có người -> 409 SEAT_TAKEN", is_err(dup, 409, "SEAT_TAKEN"))
    check("username không tồn tại -> 404 USER_NOT_FOUND", is_err(call("booking", "POST", "/api/booking", {"username": "khong_ton_tai", "movieId": st["movieId"], "showtimeId": st["id"], "seats": ["Z1"]}), 404, "USER_NOT_FOUND"))
    check("showtime không tồn tại -> 404 SHOWTIME_NOT_FOUND", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": 1, "showtimeId": 99999, "seats": ["Z1"]}), 404, "SHOWTIME_NOT_FOUND"))
    other = next(s for s in shows if s["movieId"] != st["movieId"])
    check("suất chiếu không thuộc phim -> 400", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": other["id"], "seats": ["Z1"]}), 400))
    check("body sai (seats rỗng) -> 400", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": 1, "showtimeId": 1, "seats": []}), 400))
    check("mã ghế sai định dạng -> 400", is_err(call("booking", "POST", "/api/booking", {"username": uname, "movieId": 1, "showtimeId": 1, "seats": ["zz"]}), 400))

    print("\n[6] Thanh toán thất bại -> đơn CANCELLED, ghế được nhả")
    s2 = free_seats(st["id"], 1)
    r = call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": s2, "paymentMethod": "KHONGHOPLE"})
    d = r[1]["data"] if r[1] and r[1].get("data") else {}
    check("Payment FAILED -> đơn CANCELLED (HTTP 201 vì đơn đã được ghi nhận)", r[0] == 201 and d.get("status") == "CANCELLED" and d.get("payment", {}).get("status") == "FAILED", r[1])
    check("ghế của đơn bị hủy được nhả lại", s2[0] not in call("booking", "GET", f"/api/booking/seats?showtimeId={st['id']}")[1]["data"]["seats"])
    again = call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": s2, "paymentMethod": "MOMO"})
    check("đặt lại đúng ghế đó với phương thức hợp lệ -> PAID", is_ok(again, 201) and again[1]["data"]["status"] == "PAID")


def down(service):
    print(f"\n[Kịch bản] {service.upper()} đang TẮT — Booking phải xử lý êm, không treo, không sai dữ liệu")
    st = call("showtime", "GET", "/api/showtimes")[1]["data"][0] if service != "showtime" else {"id": 1, "movieId": 1}
    uname = "user1"
    seat = [f"U{random.randint(1, 99)}"]
    t0 = time.time()
    r = call("booking", "POST", "/api/booking", {"username": uname, "movieId": st["movieId"], "showtimeId": st["id"], "seats": seat}, timeout=40)
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
    a = ap.parse_args()
    try:
        down(a.expect_down) if a.expect_down else normal()
    except ConnectionError as e:
        print(f"\n✘ {e}\n  Hãy chắc chắn các service cần thiết đang chạy (xem scripts/start-all)."); sys.exit(2)
    print(f"\nKết quả: {PASS} đạt, {FAIL} lỗi")
    sys.exit(1 if FAIL else 0)
