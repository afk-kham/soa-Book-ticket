# SOA Đặt vé phim — Bộ khung Python / FastAPI / SQLite

> **Trạng thái: KHUNG (scaffold).** Chưa có nghiệp vụ, chưa có CRUD, chưa có schema SQLite.
> Mỗi service chỉ khởi động được và trả `GET /health`. Toàn bộ nghiệp vụ do 6 thành viên viết tiếp theo README của mình.
> Mã nguồn cũ (PHP/Java/C#/Node/Go/Python thuần) **giữ nguyên** trong `services/` để đối chiếu hành vi.

## 1. Mục tiêu và kiến trúc

Đồ án SOA đặt vé phim gồm **6 service độc lập**, giao tiếp **chỉ bằng HTTP + JSON**, mỗi service **một CSDL riêng** (database-per-service). Theo quyết định mới của nhóm, cả 6 service viết lại bằng **Python 3.12 + FastAPI + SQLite**, kiến trúc phân lớp:

```
HTTP request → Router → Controller → Service → Repository → SQLite
                 │          │           │           │
              (api/)  (controllers/) (services/) (repositories/)
                       Schema (schemas/) = dữ liệu API  |  Entity (entities/) = dữ liệu nội bộ
```

Nguyên tắc **không đổi** (kế thừa `ARCHITECTURE.md` gốc): mỗi service là một tiến trình riêng, không import code của nhau, không đọc DB của nhau, Booking là orchestrator duy nhất, mọi lời gọi liên service có timeout, cấu hình qua biến môi trường.

| | Giá trị |
|---|---|
| Python | **3.12.x** (Docker: `python:3.12.12-slim-bookworm`; không nâng 3.13+) |
| Web framework | FastAPI `0.162.0` + Uvicorn `0.54.0` (đã pin trong `requirements.txt`) |
| Thư viện bổ sung | `PyJWT 2.15.1` (cả 6), `httpx 0.28.1` (Showtime, Booking), `bcrypt 5.0.0` (User) — xem `docs/ARCHITECTURE.md` §6 |
| CSDL | SQLite (thư viện chuẩn `sqlite3`), **mỗi service một file** |
| Container | Docker + Docker Compose |

## 2. Service, trách nhiệm, thành viên, cổng

| TV | Service | Cổng | Trách nhiệm | Gọi tới | README |
|---|---|---:|---|---|---|
| TV1 | Movie | 5001 | Danh mục phim | — | [movie/README.md](movie/README.md) |
| TV2 | Showtime | 5002 | Suất chiếu, giá vé, tự xếp lịch | Movie | [showtime/README.md](showtime/README.md) |
| TV3 | User/Auth | 5003 | Đăng ký, đăng nhập, tra cứu user | — | [user/README.md](user/README.md) |
| TV4 | Booking | 5004 | Đặt/thanh toán/hủy vé, **điều phối** | User, Movie, Showtime, Payment, Notification | [booking/README.md](booking/README.md) |
| TV5 | Payment | 5005 | Ghi nhận giao dịch thanh toán | — | [payment/README.md](payment/README.md) |
| TV6 | Notification | 5006 | Gửi thông báo giả lập + nhật ký | — | [notification/README.md](notification/README.md) |
| Nhóm trưởng | Tích hợp | 8080 / 8081 | Hợp đồng API, Compose, Admin, Client, test liên service | — | file này + `docs/` |

Admin (8081) và Client (8080) là HTML/CSS/JS tĩnh, **giữ nguyên**, gọi service **trực tiếp từ trình duyệt** qua `http://<host>:<port>` → Compose phải publish đúng cổng 5001–5006 ra máy host.

## 3. Cấu trúc thư mục

```
services-py/
├── README.md                  ← file này (README chung)
├── API_CONTRACT.md            ← bảng hợp đồng đã đối chiếu source (xem §8)
├── docker-compose.yml         ← 6 service, volume SQLite riêng từng service
├── .env.example               ← biến cho compose (cổng host, HOLD_MINUTES…)
├── .gitignore                 ← chặn *.db, .env
├── docs/
│   ├── AUDIT_REPORT.md        ← kết quả audit repo + ZIP, bảng mapping, mâu thuẫn
│   ├── ARCHITECTURE.md        ← vai trò từng lớp, luồng liên service, quy tắc SQLite
│   ├── MIGRATION_TRACKER.md   ← bảng theo dõi chuyển đổi từng endpoint
│   ├── OPEN_QUESTIONS.md      ← quyết định cần nhóm xác nhận (D-01 … D-19)
│   ├── ASSETS_GUIDE.md        ← file nặng/frontend phải giữ nguyên, cách bổ sung
│   └── HUONG_DAN_AP_DUNG.md   ← cách áp dụng khung vào repo, kiểm tra diff, push
└── <movie|showtime|user|booking|payment|notification>/
    ├── app/
    │   ├── main.py            ← FastAPI app + CORS + include router
    │   ├── api/router.py      ← route (hiện chỉ /health)
    │   ├── controllers/       ← (trống, TODO)
    │   ├── services/          ← (trống, TODO) nghiệp vụ
    │   ├── repositories/      ← (trống, TODO) SQL
    │   ├── entities/          ← (trống, TODO) dữ liệu nội bộ
    │   ├── schemas/           ← (trống, TODO) Pydantic request/response
    │   ├── db/connection.py   ← mở kết nối SQLite (không tạo bảng/dữ liệu)
    │   └── core/config.py     ← đọc biến môi trường
    ├── tests/test_scaffold.py ← test khung (health, không tự tạo DB)
    ├── requirements.txt / requirements-dev.txt / pytest.ini
    ├── Dockerfile / .dockerignore / .env.example
    └── README.md              ← README riêng của thành viên
```

**Vì sao thư mục tên `services-py/` mà không phải `services/`?** `services/<tên>/` hiện chứa mã nguồn cũ, kèm `README.md`, `.env.example`, `requirements.txt` trùng tên với file khung. Đặt cạnh nhau để **không ghi đè và không xóa** bất cứ thứ gì. Khi một service Python đã đạt tiêu chí tương đương, nhóm mới thực hiện cutover (xem `docs/OPEN_QUESTIONS.md` D-02).

## 4. Thiết lập môi trường (chạy local từng service)

```bash
cd services-py/movie                 # đổi tên service tương ứng
python3.12 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                 # KHÔNG commit .env
uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload  # đúng cổng của service
curl http://localhost:5001/health
```

Phản hồi mong đợi: `{"status":"success","data":{"service":"movie-service","port":5001}}`.
Tài liệu OpenAPI tự sinh: `http://localhost:5001/docs`.

## 5. Docker Compose

```bash
cd services-py
cp .env.example .env        # tùy chọn: chỉ để đổi cổng host nếu bị trùng
docker compose config       # kiểm tra cấu hình hợp lệ
docker compose up --build   # build + chạy cả 6 service
curl http://localhost:5001/health ... 5006
docker compose down         # dừng (volume SQLite được giữ). KHÔNG dùng `down -v` nếu muốn giữ dữ liệu
```

- Cổng **publish ra host** (`5001:5001`…) khác khái niệm với cổng **nội bộ container**. Hiện hai giá trị trùng số; nếu đổi `*_HOST_PORT` thì chỉ đổi phía host, URL giữa các container vẫn là `http://movie:5001`.
- Không có `depends_on` giữa các service nghiệp vụ (tắt một service, các service còn lại vẫn chạy — yêu cầu SOA).
- Admin/Client **chưa** nằm trong Compose (chạy như cũ: `python3 -m http.server 8080/8081`). Không có reverse proxy / API Gateway.

## 6. Bảng cổng và biến môi trường

| Service | Cổng nội bộ = cổng host mặc định | Biến riêng (ngoài `HOST`, `PORT`, `DB_PATH`) |
|---|---:|---|
| Movie | 5001 | `JWT_SECRET` |
| Showtime | 5002 | `MOVIE_SERVICE_URL`, `VALIDATE_MOVIE`, `AUTO_SCHEDULE_DAYS`, `APP_TIMEZONE`, `JWT_SECRET` |
| User | 5003 | `JWT_SECRET` |
| Booking | 5004 | `USER_/MOVIE_/SHOWTIME_/PAYMENT_/NOTIFICATION_SERVICE_URL`, `UPSTREAM_TIMEOUT_SECONDS`, `HOLD_MINUTES`, `JWT_SECRET`, `INTERNAL_KEY` |
| Payment | 5005 | `JWT_SECRET` |
| Notification | 5006 | `JWT_SECRET`, `INTERNAL_KEY` |

`JWT_SECRET` và `INTERNAL_KEY` **để trống** trong khung; cả nhóm dùng chung một khóa (>= 32 ký tự), điền ở máy mình, **không commit**.

Biến `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD` (MySQL) và `MONGO_URI/MONGO_DB` (Payment) **không còn dùng** — thay bằng `DB_PATH`. Đây là thay đổi so với `API_CONTRACT.md` §1 → cần PR sửa hợp đồng (D-05).

## 7. Vị trí lưu database SQLite

| Môi trường | Đường dẫn | Ghi chú |
|---|---|---|
| Local | `services-py/<service>/data/<tên>.db` | `*.db` và `data/` bị `.gitignore`; **không commit** |
| Docker | `/data/<tên>.db` trong volume `<service>_data` | Mỗi service **một volume riêng**; không mount chung |

Tên file: `movie.db`, `showtime.db`, `user.db`, `booking.db`, `payment.db`, `notification.db`.

- **Không để hai service cùng ghi một file SQLite.** Một service = một file = một volume. Mỗi service chạy **một** tiến trình Uvicorn (không `--workers N`) cho tới khi nhóm chốt cấu hình đồng thời (D-03, D-10).
- **Sao lưu đề xuất:** dừng service hoặc dùng `sqlite3 <file> ".backup '<đích>'"` (an toàn khi đang chạy, nhất quán với WAL); lưu ngoài repo. Với volume Docker: `docker run --rm -v soa-book-ticket-py_movie_data:/data -v "$PWD":/bk alpine cp /data/movie.db /bk/movie.db.bak` sau khi `docker compose stop movie`.
- **Quyền truy cập:** user `appuser` (uid 10001) sở hữu `/data`; chỉ service tương ứng mount volume đó.
- Khung **không tạo** DB, **không nạp** seed. Việc chuyển dữ liệu MySQL/MongoDB → SQLite là **migration riêng** (xem `docs/MIGRATION_TRACKER.md`), không thực hiện ở giai đoạn dựng khung.

## 8. Hợp đồng API và giao tiếp liên service

- **Nguồn sự thật hiện hành vẫn là `API_CONTRACT.md` ở thư mục gốc repo.** Muốn đổi → PR, ≥ 2 người duyệt, cập nhật `CHANGELOG.md` (Điều 8 của hợp đồng gốc).
- [`API_CONTRACT.md`](API_CONTRACT.md) trong thư mục này là **bảng chi tiết đã đối chiếu với source thực tế** (request/response/lỗi/phụ thuộc/trạng thái). Hai file mâu thuẫn → báo nhóm trưởng, không tự chọn.
- Luồng liên service (đặt vé, thanh toán sau, hủy, Showtime→Movie): xem [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §4.
- Không hard-code URL service khác: đọc từ `app/core/config.py` (nguồn: biến môi trường).

## 9. Chạy test

```bash
cd services-py/<service> && python -m pytest -q      # test khung của service
python3 tests/integration/run_tests.py                # test tích hợp gốc (thư mục gốc repo)
```

Test khung chỉ chứng minh app khởi động + `/health` + không tự tạo file DB. **Chưa có test nghiệp vụ.** Bộ `tests/integration/run_tests.py` gốc nhắm vào các service cũ; chỉ dùng được với service Python khi service đó đã cài đặt đủ hành vi (hiện chưa).
Lưu ý: pytest in cảnh báo `StarletteDeprecationWarning` về `httpx` — chỉ là cảnh báo của TestClient, không ảnh hưởng chạy.

## 10. Phân công & quy trình Git

| TV | Nhánh | Thư mục được sửa |
|---|---|---|
| TV1 | `feature/tv1-movie` | `services-py/movie/` |
| TV2 | `feature/tv2-showtime` | `services-py/showtime/` |
| TV3 | `feature/tv3-user` | `services-py/user/` |
| TV4 | `feature/tv4-booking` | `services-py/booking/` |
| TV5 | `feature/tv5-payment` | `services-py/payment/` |
| TV6 | `feature/tv6-notification` | `services-py/notification/` |
| Nhóm trưởng | `develop` | `services-py/` cấp gốc (`docker-compose.yml`, `docs/`, `API_CONTRACT.md`, `.env.example`), `admin/`, `client/`, `tests/`, `scripts/` |

1. `git checkout develop && git pull` → `git checkout feature/tvN-…` (rebase/merge từ `develop` thường xuyên).
2. Commit nhỏ, thông điệp rõ: `feat(movie): thêm GET /api/movies`.
3. Trước PR: chạy `pytest` của service + kiểm tra `/health` + chạy Compose.
4. PR vào `develop`; **cần 1 người khác duyệt**; không tự merge PR của mình.
5. `main` chỉ nhận từ `develop` sau `INTEGRATION_CHECKLIST.md`. **Không force-push**, không rewrite history.
6. File dùng chung (bảng sở hữu ở §11) chỉ sửa qua nhóm trưởng.

## 11. Ai sở hữu file dùng chung

| File | Người sở hữu | Quy trình đổi |
|---|---|---|
| `services-py/docker-compose.yml`, `.env.example`, `.gitignore` | Nhóm trưởng | Mở Issue/PR, nhóm trưởng duyệt |
| `services-py/API_CONTRACT.md`, `API_CONTRACT.md` (gốc) | Nhóm trưởng | PR + ≥ 2 duyệt (gồm chủ service bị ảnh hưởng) + `CHANGELOG.md` |
| `services-py/docs/*` | Nhóm trưởng | PR |
| `services-py/<svc>/**` | TV tương ứng | PR vào `develop` |
| `app/main.py`, `core/config.py`, `Dockerfile` của service | TV tương ứng, **nhưng giữ đúng cổng/tên biến** | PR; đổi cổng/tên biến phải qua nhóm trưởng |

## 12. Chưa triển khai / chờ xác nhận

- Toàn bộ nghiệp vụ, CRUD, repository, schema SQLite, seed, migration dữ liệu: **chưa làm**.
- Error envelope `{status,code,message}` thống nhất, `OPTIONS → 204`, 422 → 400 `VALIDATION_ERROR`: **chưa làm** (D-07).
- Docker image **chưa được build thử** trong môi trường dựng khung (không có Docker); xem `docs/HUONG_DAN_AP_DUNG.md` §3 để tự kiểm tra.
- 19 điểm cần quyết định: [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md). Quan trọng nhất: **D-19** (xác nhận với giảng viên về FastAPI/Python/SQLite), **D-01** (xác nhận SQLite vì repo hiện là MySQL/MongoDB), **D-04** (kiểu `id` của Payment), **D-09/D-10** (khóa/đồng thời với SQLite).
