# TV4 — Booking Service (Python / FastAPI / SQLite) — cổng 5004

> **Trạng thái: KHUNG.** Service chỉ khởi động và trả `GET /health`. Mọi nghiệp vụ do **TV4** viết theo README này.
> Nhánh làm việc: `feature/tv4-booking` (không làm trực tiếp trên `main`/`develop`). Đọc trước: [README chung](../README.md), [API_CONTRACT.md](../API_CONTRACT.md) §5, [ARCHITECTURE](../docs/ARCHITECTURE.md), [OPEN_QUESTIONS](../docs/OPEN_QUESTIONS.md).

## 1. Mục tiêu và phạm vi trách nhiệm

**Orchestrator** của luồng đặt vé: kiểm tra User/Movie/Showtime, giữ ghế, gọi Payment, gọi Notification, tự hủy đơn quá hạn. Là service có nhiều logic liên service nhất.

Bạn **chỉ** sở hữu: `services-py/booking/`, `database/booking/` (schema/seed cũ — chỉ đọc), `docs/tv4-booking/` (tài liệu). Không sửa service khác, Admin, Client, hợp đồng chung.

## 2. API và nghiệp vụ đã xác minh từ source

Bảng đầy đủ (request/response/mã HTTP/lỗi) ở [API_CONTRACT.md](../API_CONTRACT.md) mục 5. Quy tắc phải giữ nguyên (đọc từ `services/booking/` — mã cũ là nguồn đối chiếu):

- Trạng thái đơn chỉ gồm `PENDING | PAID | CANCELLED`; ghế được coi là giữ khi `PENDING` hoặc `PAID`; `CANCELLED` nhả ghế. `seats` lưu `"A1,A2"`, API trả mảng.
- Giá **luôn lấy từ Showtime** (`price × số ghế`); không tin giá client. Suất không thuộc phim → 400; suất đã bắt đầu → 400 `SHOWTIME_CLOSED`.
- Ghế hợp lệ `^[A-Z]\d{1,2}$`, 1–10 ghế, không trùng; ghế đã giữ → 409 `SEAT_TAKEN` (chống đặt trùng bằng khóa — D-10).
- `payNow:false` → chỉ giữ ghế, trả `PENDING` + `expiresAt` (= `createdAt` + `HOLD_MINUTES`), chưa gọi Payment; quá hạn tự `CANCELLED`.
- `POST /{id}/pay`: kiểm tra chủ đơn (403 `FORBIDDEN`); thất bại/Payment sập → đơn **vẫn PENDING**; đã trả → 409 `ALREADY_PAID`; đã hủy/hết hạn → 409 `BOOKING_CANCELLED`.
- `POST /{id}/cancel`: `PAID` → 409 `PAID_NOT_CANCELLABLE`.
- Timeout: upstream 5s (`UPSTREAM_TIMEOUT_SECONDS`), Notification 3s, hỏi lại Payment 2s. Payment sập → hỏi lại `GET /api/payment?bookingId=` rồi mới hủy. Notification lỗi **không** làm hỏng đơn `PAID` (`notification: FAILED`).
- **Không** tạo PUT/DELETE CRUD chung (sẽ phá nghiệp vụ đặt/trả/hủy).
- `GET /health` phải **ping DB**.

Ngoài bảng này **không thêm endpoint nào** nếu chưa có PR sửa `API_CONTRACT.md` được duyệt.

## 3. Cây thư mục và chức năng từng file

```
booking/
├── README.md                  ← file này
├── Dockerfile                 ← image Python 3.12, user không phải root, volume /data, HEALTHCHECK
├── .dockerignore
├── .env.example               ← mẫu biến môi trường (chép thành .env, KHÔNG commit)
├── requirements.txt           ← fastapi, uvicorn + thư viện đã chốt cho service (xem §10); thêm gói khác bằng PR
├── requirements-dev.txt       ← + pytest, httpx (chỉ để test)
├── pytest.ini                 ← pythonpath=. , testpaths=tests
├── app/
│   ├── __init__.py
│   ├── main.py                ← tạo FastAPI app, CORS, include router (KHUNG)
│   ├── api/
│   │   ├── __init__.py
│   │   └── router.py          ← APIRouter: hiện chỉ GET /health. **Thêm route nghiệp vụ tại đây**
│   ├── controllers/__init__.py   ← (trống) nhận request → gọi service
│   ├── services/__init__.py      ← (trống) **logic nghiệp vụ**
│   ├── repositories/__init__.py  ← (trống) **SQL SQLite**
│   ├── entities/__init__.py      ← (trống) dữ liệu nội bộ (snake_case)
│   ├── schemas/__init__.py       ← (trống) Pydantic request/response (camelCase)
│   ├── db/
│   │   ├── __init__.py        ← TODO khởi tạo schema/migration (chờ D-03)
│   │   └── connection.py      ← get_connection(): mở SQLite tại DB_PATH (không tạo bảng/dữ liệu)
│   └── core/
│       ├── __init__.py
│       └── config.py          ← đọc biến môi trường (SERVICE_NAME, PORT, DB_PATH, ...)
└── tests/
    ├── __init__.py
    └── test_scaffold.py       ← test khung (health, không tự tạo DB). Thêm test nghiệp vụ tại đây
```

Ánh xạ từ mã nguồn cũ:

| File cũ trong `services/booking/` (giữ nguyên, chỉ đọc) | Chuyển sang |
|---|---|
| `Program.cs` | route + luồng đặt/trả/hủy → `api/`, `controllers/`, `services/` |
| `Upstream.cs` | gọi HTTP service khác + timeout + map lỗi → `services/` (client HTTP) |
| `BookingStore.cs` | SQL (có chế độ `memory` chỉ để test) → `repositories/` |
| `Models.cs` | `Booking`, `ApiException` → `entities/`, `schemas/`, `core/` |
| `Config.cs` | → `core/config.py` |

## 4. File bạn được phép sửa

- Toàn bộ `services-py/booking/app/**` và `services-py/booking/tests/**`.
- `services-py/booking/requirements*.txt` (thêm dependency thật sự cần, pin phiên bản, ghi lý do trong PR).
- `services-py/booking/.env.example`, `Dockerfile`, `README.md` — nhưng **giữ nguyên cổng 5004, tên biến, tên file DB**.
- Thêm file/thư mục con trong các lớp hiện có. Không tạo thêm lớp trùng chức năng (`dao/`, `models/`…).

## 5. File dùng chung — KHÔNG tự ý sửa

| File | Người sở hữu | Muốn đổi thì |
|---|---|---|
| `services-py/docker-compose.yml`, `services-py/.env.example`, `services-py/.gitignore` | Nhóm trưởng | Mở Issue, nhóm trưởng sửa |
| `services-py/API_CONTRACT.md`, `API_CONTRACT.md` (gốc) | Nhóm trưởng | PR + ≥ 2 người duyệt + `CHANGELOG.md` |
| `services-py/docs/*`, `services-py/README.md` | Nhóm trưởng | PR |
| `admin/`, `client/`, `tests/`, `scripts/`, `ui-seed/` | Nhóm trưởng | Mở Issue |
| `services-py/<service khác>/**`, `services/**` (mã cũ) | Người khác / giữ nguyên | Mở Issue mô tả bước tái hiện; **không sửa hộ** |

Nếu cần sửa chung một file với người khác: người sở hữu ở bảng trên quyết định; người cần đổi mở Issue/PR và gắn @người sở hữu.

## 6. Thứ tự triển khai (Router → Controller → Service → Repository, kèm Entity & Schema)

Làm **từng endpoint một**, theo thứ tự trong bảng `MIGRATION_TRACKER.md`:

1. **Schema** (`schemas/`): Pydantic request/response đúng tên trường camelCase của hợp đồng.
2. **Entity** (`entities/`): đối tượng dữ liệu nội bộ (cột snake_case).
3. **Repository** (`repositories/`): SQL tham số hóa (`?`) dùng `db.connection.get_connection()`; không có quy tắc nghiệp vụ.
4. **Service** (`services/`): nghiệp vụ; không biết HTTP, không viết SQL.
5. **Controller** (`controllers/`): nhận request → gọi service → dựng envelope `{status,data}`/lỗi.
6. **Router** (`api/router.py`): khai báo path/method/mã HTTP, nối controller.
7. **Test** (`tests/`): đủ cho hành vi cũ, validation, lỗi, mã HTTP, DB tạm.
8. Cập nhật `MIGRATION_TRACKER.md`.

Lớp nào cũng **chỉ gọi xuống** lớp dưới nó. Không import code của service khác.

## 7. Quy tắc SQLite, schema và migration

- Một file `booking.db`, **chỉ service này** mở. Local: `./data/booking.db`; Docker: `/data/booking.db` (volume `booking_data`). `*.db` bị `.gitignore` — **không commit**.
- Schema cũ (MySQL) để **đối chiếu**: `bookings(id INT AUTO_INCREMENT PK, movie_id INT NN, showtime_id INT NN, username VARCHAR(50) NN, seats VARCHAR(100) NN, total_price INT NN, status VARCHAR(10) NN DEFAULT 'PENDING', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)` + index `(showtime_id,status)`, `(username)` + CHECK `status IN (...)`, `total_price >= 0`.
- Seed cũ: `database/booking/seed.sql` (3 đơn: PAID / CANCELLED / PENDING); `booking_db.sqlserver.sql` **không dùng**. **Không chạy** các file `schema.sql`/`seed.sql`/`seed.js` cũ (có `DROP`/`DELETE`/`drop()`).
- Khi viết schema SQLite: `CREATE TABLE IF NOT EXISTS`, idempotent, **không `DROP`**, không tự nạp dữ liệu lúc import/khởi động; giữ nguyên id và giá trị seed cũ (thêm dữ liệu mới = id lớn hơn).
- Việc tạo schema và nạp dữ liệu là bước **tường minh** (script/lệnh), chỉ làm sau khi nhóm chốt D-01, D-03, D-16. Chuyển dữ liệu thật từ nguồn cũ là **migration riêng**: sao lưu trước, đối chiếu sau (xem `docs/MIGRATION_TRACKER.md` §3).
- Test dùng DB tạm (`tmp_path`), **không** dùng file dữ liệu thật; không test hành vi xóa trên dữ liệu thật.

## 8. Dependency với service khác

- **Service này gọi:** **User, Movie, Showtime, Payment, Notification** (HTTP). Không đọc DB của họ.
- **Được gọi bởi:** Client, Admin (gọi trực tiếp). Payment/Notification **không** gọi ngược Booking.
- Chỉ qua **HTTP + JSON** theo hợp đồng; không import code, không đọc DB của nhau. Mọi lời gọi ra ngoài phải có timeout và xử lý lỗi theo bảng `docs/ARCHITECTURE.md` §4.4.

## 9. Hợp đồng request/response phải tuân thủ

Đúng như [API_CONTRACT.md](../API_CONTRACT.md) §1 (quy ước chung) và §5: envelope `{"status":"success","data":…}` / `{"status":"error","code","message"}`, JSON camelCase, tiền là số nguyên VND, thời gian đúng định dạng của service, message lỗi tiếng Việt, không lộ lỗi SQL/stack. **Không tự đổi** path, method, tên trường, mã HTTP, mã lỗi. Phát hiện sai khác với code cũ → ghi vào PR/Issue, không "sửa cho đẹp".

## 10. Cổng, biến môi trường, URL nội bộ

| Biến | Giá trị khi chạy local | Giá trị trong Docker Compose | Ý nghĩa |
|---|---|---|---|
| `HOST` | `0.0.0.0` | `0.0.0.0` | Địa chỉ lắng nghe |
| `PORT` | `5004` | `5004` | Cổng trong container/tiến trình — **không đổi** (theo hợp đồng) |
| `DB_PATH` | `./data/booking.db` | `/data/booking.db` | File SQLite **riêng** của service |
| `USER_SERVICE_URL` | `http://localhost:5003` | `http://user:5003` | URL User Service |
| `MOVIE_SERVICE_URL` | `http://localhost:5001` | `http://movie:5001` | URL Movie Service |
| `SHOWTIME_SERVICE_URL` | `http://localhost:5002` | `http://showtime:5002` | URL Showtime Service |
| `PAYMENT_SERVICE_URL` | `http://localhost:5005` | `http://payment:5005` | URL Payment Service |
| `NOTIFICATION_SERVICE_URL` | `http://localhost:5006` | `http://notification:5006` | URL Notification Service |
| `UPSTREAM_TIMEOUT_SECONDS` | `5` | `5` | Timeout gọi service khác (mặc định 5; Notification 3) |
| `HOLD_MINUTES` | `10` | `10` | Số phút giữ ghế đơn `PENDING` (mặc định 10) |
| `JWT_SECRET` | `(trống)` | `${JWT_SECRET:-}` | Khóa JWT HS256 **dùng chung cả nhóm** (>= 32 ký tự, UTF-8 thô). Để trống trong khung; điền ở máy mình, **không commit khóa thật** |
| `INTERNAL_KEY` | `(trống)` | `${INTERNAL_KEY:-}` | Khóa nội bộ Booking → Notification (header `X-Internal-Key`); **không commit khóa thật** |

### Thư viện đã khai báo trong `requirements.txt` (pin cố định)

| Gói | Phiên bản | Dùng cho |
|---|---|---|
| `fastapi` | 0.162.0 | Web framework (khung) |
| `uvicorn` | 0.54.0 | Chạy ứng dụng (khung) |
| `PyJWT` | 2.15.1 | Verify JWT; `username` lấy từ token |
| `httpx` | 0.28.1 | Gọi User, Movie, Showtime, Payment, Notification (timeout 5s/3s/2s) — chốt đồng bộ/bất đồng bộ cùng nhóm, D-11 |

Không thêm gói khác khi chưa cần; thêm bằng PR, **pin phiên bản**, nói rõ lý do (D-11). `sqlite3` là thư viện chuẩn của Python nên không cần cài. Sau khi sửa `requirements.txt` phải build lại image (`docker compose build booking`).

### Xác thực cuối kỳ (kế hoạch v2.1, mục 5) — áp dụng cho service này

- `POST /api/booking`, `GET /api/booking/{id}`: **cuối kỳ** cần JWT hợp lệ; `username` lấy từ token (không tin body).
- `GET /api/booking` (danh sách): **cuối kỳ** role `ADMIN`.
- **Chuyển tiếp nguyên header `Authorization`** sang Payment; gọi Notification kèm header `X-Internal-Key` (biến `INTERNAL_KEY`).
- `pay`, `cancel`, `seats`, `availability` **không có trong bảng v2.1** (repo hiện có) — hỏi nhóm trưởng về quyền truy cập.

Quy định JWT chung: **HS256**; khóa lấy từ biến môi trường `JWT_SECRET` (>= 32 ký tự, chuyển sang byte bằng **UTF-8 thô, không giải mã Base64**); claims `sub` (username), `userId`, `role` (`USER`/`ADMIN`), `iat`, `exp` (+2 giờ); gửi bằng `Authorization: Bearer <token>`; cho phép lệch giờ **60 giây**; thiếu/sai token → 401, đủ token nhưng thiếu quyền → 403; phải trả **204** cho `OPTIONS` (trình duyệt luôn gửi preflight khi có header `Authorization`). Khóa thật **không** được commit. Giữa kỳ các endpoint còn công khai — thời điểm bật xác thực do nhóm trưởng quyết (D-18).

- Cổng **5004** là cố định theo hợp đồng. Trong Compose, host publish `${BOOKING_HOST_PORT:-5004}` → container `5004`.
- URL gọi service khác **chỉ** được đọc từ `app/core/config.py` (nguồn: biến môi trường) — không hard-code trong lớp khác.

## 11. Chạy service và test

```bash
cd services-py/booking
python3.12 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                       # KHÔNG commit .env
uvicorn app.main:app --host 0.0.0.0 --port 5004 --reload
curl http://localhost:5004/health                        # {"status":"success","data":{"service":"booking-service","port":5004}}
python -m pytest -q                                        # test của service

# Docker (từ services-py/)
docker compose up --build booking
```

Test tích hợp liên service (`python tests/integration/run_tests.py`, thư mục gốc repo) chỉ dùng được khi các service liên quan đã được cài đặt đủ hành vi.

## 12. Checklist hoàn thành

- [ ] Đã đọc mã cũ `services/booking/` và ghi lại sai khác với contract (nếu có) vào PR.
- [ ] Mọi endpoint ở `API_CONTRACT.md` §5 đã cài đặt, khớp path/method/envelope/camelCase/mã HTTP/mã lỗi.
- [ ] Validation đủ (body rỗng, JSON sai, kiểu dữ liệu, giới hạn độ dài); không crash khi body rỗng/sai JSON.
- [ ] `/health`, `OPTIONS → 204`, CORS `*` đúng (sau khi nhóm chốt D-07).
- [ ] Schema SQLite idempotent, seed giữ nguyên id/giá trị; không có `DROP`.
- [ ] Không lộ trường nhạy cảm, lỗi SQL, stack trace.
- [ ] Test của service pass (DB tạm); `docker compose up --build booking` chạy và `/health` OK.
- [ ] Chạy lại các nhóm [kịch bản lỗi] trong `INTEGRATION_FLOW.md` §2 với service đối tác tắt (503/`FAILED`/`SKIPPED`).
- [ ] Hai request đặt cùng ghế đồng thời: đúng một request thành công.
- [ ] Cập nhật README này và `docs/MIGRATION_TRACKER.md`; không commit `.env`, `*.db`, `__pycache__/`.
- [ ] PR vào `develop`, có 1 người khác duyệt (không tự merge).

## 13. File nặng — người dùng tự bổ sung / giữ nguyên

Khung **không tạo** và **không di chuyển** file nặng. Bảng cho biết nơi đặt và hiện trạng:

| Loại file | Vị trí đích / hiện có | Hiện có? | Việc cần làm (thủ công) |
|---|---|---|---|
| Sơ đồ ERD/DFD/UC | docs/tv4-booking/ | Có (`ERD/DFD0/1/2/UC_booking`) | Giữ nguyên |
| Báo cáo | docs/tv4-booking/ | Có (`05_baocao_booking.docx`, `reports/05_baocao_booking.pdf`) | Giữ nguyên |
| Ảnh kết quả chạy | docs/tv4-booking/anh-ket-qua/ | Có (9 PNG) | Giữ nguyên; ảnh mới thêm tên mới |
| Bản giữa kỳ tham khảo (C#, docker-compose, SQL) | docs/tv4-booking/source-giua-ky/ | Có | Chỉ tham khảo; không sửa, không build |
| Trang Admin giữa kỳ | docs/tv4-booking/admin_booking_giua_ky.html | Có | Giữ nguyên |

Quy tắc chung (xem [ASSETS_GUIDE](../docs/ASSETS_GUIDE.md)): file cũ giữ nguyên tên và đường dẫn; file mới đặt tên mới cạnh file cũ; HTML đang tham chiếu ảnh nào thì không đổi đường dẫn ảnh đó.

## 14. Vấn đề chưa rõ — hỏi nhóm trưởng trước khi triển khai

- D-01, D-04 (**`payment.id` phải là chuỗi**, code cũ đọc `GetString()`), D-07, D-10 (khóa ghế/đồng thời với SQLite), D-11 (HTTP client), D-18.
- `created_at` ghi theo **giờ máy Booking** (không phải giờ SQLite/UTC) và `expiresAt` tính từ đó — giữ nguyên hành vi, kiểm tra múi giờ container.
- Code cũ ưu tiên kết nối IPv4 khi gọi service khác (tránh trễ ~1s trên Windows). Trong Docker không cần; xác nhận khi chạy local Windows.

Danh sách đầy đủ và trạng thái: [OPEN_QUESTIONS.md](../docs/OPEN_QUESTIONS.md).
