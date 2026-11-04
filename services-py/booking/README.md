# TV4 — Booking Service (Python / FastAPI / SQLite) — cổng 5004

> **Trạng thái: ĐÃ CÀI ĐẶT ĐỦ NGHIỆP VỤ** theo [API_CONTRACT.md](../API_CONTRACT.md) §5: 9 endpoint + `/health`, chống đặt trùng ghế, giữ ghế có hạn, điều phối 5 service, xử lý khi đối tác lỗi. JWT đã có nhưng **tắt mặc định** (xem §10, chờ D-18).
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
- `PUT /{id}`: chỉ đổi ghế của đơn `PENDING` (giá = đơn giá cũ × số ghế mới, hạn giữ không đổi). `DELETE /{id}?username=`: xóa hẳn đơn ở mọi trạng thái. Đặt/trả/hủy vẫn đi qua `POST`.
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
│   ├── main.py                ← tạo FastAPI app, vòng quét đơn quá hạn mỗi 30 giây
│   ├── api/
│   │   ├── router.py          ← khai báo path/method/mã HTTP, nối sang controller
│   │   └── deps.py            ← lắp Repository → Service → Controller
│   ├── controllers/
│   │   └── booking_controller.py  ← đọc body (giới hạn 64 KiB), kiểm tra query, dịch mã lỗi ra mã HTTP
│   ├── services/
│   │   ├── booking_service.py     ← **nghiệp vụ điều phối**: đặt, thanh toán, hủy, hết hạn, đối soát Payment
│   │   └── upstream.py            ← gọi HTTP sang 5 service (timeout, 503 khi không với tới được)
│   ├── repositories/
│   │   └── booking_repository.py  ← **toàn bộ SQL**, giao dịch `BEGIN IMMEDIATE`
│   ├── entities/booking.py    ← dữ liệu nội bộ (snake_case), hằng trạng thái, `expires_at`
│   ├── schemas/booking.py     ← Pydantic request/response (camelCase), thứ tự và thông báo lỗi như mã cũ
│   ├── db/
│   │   ├── connection.py      ← get_connection(): WAL + busy_timeout, tự commit/rollback
│   │   ├── schema.sql         ← bảng `bookings`, 2 index, 2 CHECK (idempotent, không DROP)
│   │   ├── seed.sql           ← 3 đơn mẫu giữ nguyên id/giá trị (`INSERT OR IGNORE`)
│   │   └── init_db.py         ← `python -m app.db.init_db [--seed]`
│   └── core/
│       ├── config.py          ← biến môi trường, tự nạp `.env` khi chạy local
│       ├── clock.py           ← đồng hồ theo `APP_TIMEZONE`
│       ├── errors.py          ← `BookingError(code, message)`
│       ├── http.py            ← envelope, CORS, `OPTIONS → 204`, 404/405/500 (D-07)
│       └── jwt_auth.py        ← verify JWT HS256 (chỉ dùng khi bật `JWT_REQUIRED`)
└── tests/
    ├── conftest.py            ← DB tạm, giả lập 5 đối tác bằng `httpx.MockTransport`
    ├── test_scaffold.py       ← test khung
    ├── test_booking_api.py    ← hợp đồng API: envelope, validation, mã HTTP, mã lỗi
    ├── test_booking_flow.py   ← điều phối: đặt trùng ghế, Payment/Notification lỗi, hết hạn, đồng thời
    └── test_infrastructure.py ← schema/seed, múi giờ, cấu hình, vòng quét, JWT
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
- Việc tạo schema và nạp dữ liệu là bước **tường minh**: `python -m app.db.init_db [--seed]`. App không tự tạo bảng lúc import hay khởi động; chưa chạy lệnh này thì mọi endpoint nghiệp vụ trả 500. Riêng Docker: `CMD` của `Dockerfile` chạy `init_db` (không `--seed`) trước Uvicorn, nên seed vẫn phải chạy tay (§11). Chuyển dữ liệu thật từ nguồn cũ là **migration riêng**: sao lưu trước, đối chiếu sau (xem `docs/MIGRATION_TRACKER.md` §3).
- **Nạp seed Booking cùng lúc với seed Payment.** Payment seed sẵn giao dịch `PAID` của đơn 1 và `FAILED` của đơn 2. Nếu Booking không seed, đơn mới đầu tiên sẽ có id 1, Payment trả `ALREADY_PAID`, Booking đối soát ra giao dịch cũ và coi là đã trả. Có seed thì đơn mới bắt đầu từ id 4.
- Chống đặt trùng ghế (D-10): "quét hết hạn + đọc ghế + lưu đơn" nằm trong một giao dịch `BEGIN IMMEDIATE`, giành quyền ghi ngay từ đầu nên không cần đổi schema và vẫn đúng nếu có nhiều tiến trình cùng ghi một file DB.
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
| `APP_TIMEZONE` | `Asia/Ho_Chi_Minh` | chưa khai báo, dùng mặc định | Múi giờ của `createdAt`, hạn giữ ghế và phép so giờ chiếu. **Phải trùng với Showtime** |
| `JWT_REQUIRED` | `false` | chưa khai báo, dùng mặc định | Công tắc xác thực cuối kỳ (D-18). Muốn bật trong Compose, nhóm trưởng cần thêm biến này vào `docker-compose.yml` |
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

Đã cài đặt, **tắt mặc định** bằng `JWT_REQUIRED=false` vì hiện User còn trả `demo-token-<username>`, Client/Admin chưa gửi header `Authorization`. Khi tắt, danh tính lấy từ body như baseline. Header `Authorization` luôn được chuyển tiếp nguyên vẹn sang Payment; `X-Internal-Key` được gửi sang Notification khi có `INTERNAL_KEY`.

Khi bật `JWT_REQUIRED=true` (thiếu/sai token → 401, thiếu quyền → 403):

| Endpoint | Quy tắc | Nguồn |
|---|---|---|
| `POST /api/booking` | JWT; `username` lấy từ claim `sub`, bỏ qua body | v2.1 §4.2 |
| `GET /api/booking/{id}` | JWT; chỉ chủ đơn hoặc `ADMIN` | v2.1 §4.2 yêu cầu JWT; **đề xuất** thêm kiểm tra chủ đơn |
| `GET /api/booking` | `ADMIN` xem tất cả; `USER` chỉ được gọi với `?username=<chính mình>` | v2.1 §4.2 ghi `ADMIN`; **đề xuất** nới cho `USER` vì trang "Vé của tôi" của Client dùng endpoint này |
| `POST .../pay`, `POST .../cancel`, `PUT`/`DELETE /api/booking/{id}` | JWT; chủ đơn lấy từ `sub`; `ADMIN` thao tác được mọi đơn | **Đề xuất**, không có trong v2.1 (D-18b). Trang Admin đang hủy đơn hộ khách |
| `GET .../seats`, `.../availability`, `/health` | Công khai | **Đề xuất**: không chứa dữ liệu cá nhân, Client vẽ sơ đồ ghế bằng các endpoint này |

Quy định JWT chung: **HS256**; khóa lấy từ biến môi trường `JWT_SECRET` (>= 32 ký tự, chuyển sang byte bằng **UTF-8 thô, không giải mã Base64**); claims `sub` (username), `userId`, `role` (`USER`/`ADMIN`), `iat`, `exp` (+2 giờ); gửi bằng `Authorization: Bearer <token>`; cho phép lệch giờ **60 giây**; thiếu/sai token → 401, đủ token nhưng thiếu quyền → 403; phải trả **204** cho `OPTIONS` (trình duyệt luôn gửi preflight khi có header `Authorization`). Khóa thật **không** được commit. Giữa kỳ các endpoint còn công khai — thời điểm bật xác thực do nhóm trưởng quyết (D-18).

- Cổng **5004** là cố định theo hợp đồng. Trong Compose, host publish `${BOOKING_HOST_PORT:-5004}` → container `5004`.
- URL gọi service khác **chỉ** được đọc từ `app/core/config.py` (nguồn: biến môi trường) — không hard-code trong lớp khác.

## 11. Chạy service và test

```bash
cd services-py/booking
python3.12 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                       # KHÔNG commit .env. Service tự nạp file này khi chạy local
python -m app.db.init_db --seed                            # tạo bảng + 3 đơn mẫu, chạy lại an toàn
uvicorn app.main:app --host 0.0.0.0 --port 5004            # không dùng --workers
curl http://localhost:5004/health                          # {"status":"success","data":{"service":"booking-service","port":5004}}
python -m pytest -q                                        # test của service
# Swagger UI: http://localhost:5004/docs

# Docker (từ services-py/). Sau khi service chạy, nạp seed của Booking cùng các service khác
docker compose up --build -d
docker compose exec booking python -m app.db.init_db --seed
```

Test tích hợp liên service: bật đủ 6 service (Movie, User, Payment, Notification phải chạy lệnh seed/init của mình trước) rồi chạy từ thư mục gốc repo:

```bash
python tests/integration/run_tests.py                       # 54 kiểm tra luồng bình thường
python tests/integration/run_tests.py --expect-down payment # tắt Payment trước; tương tự notification, user, movie, showtime
```

## 12. Checklist hoàn thành

- [x] Đã đọc mã cũ `services/booking/` và ghi lại sai khác với contract (xem §14).
- [x] Mọi endpoint ở `API_CONTRACT.md` §5 đã cài đặt, khớp path/method/envelope/camelCase/mã HTTP/mã lỗi.
- [x] Validation đủ (body rỗng, JSON sai, kiểu dữ liệu, giới hạn độ dài); không crash khi body rỗng/sai JSON.
- [x] `/health`, `OPTIONS → 204`, CORS `*` đúng (D-07 xử lý trong phạm vi service).
- [x] Schema SQLite idempotent, seed giữ nguyên id/giá trị; không có `DROP`.
- [x] Không lộ trường nhạy cảm, lỗi SQL, stack trace.
- [x] Test của service pass (263 test, DB tạm); `docker compose up --build` chạy cả 6 service và `/health` OK.
- [x] Chạy lại các nhóm [kịch bản lỗi] trong `INTEGRATION_FLOW.md` §2 với service đối tác tắt (503/`FAILED`/`SKIPPED`).
- [x] Hai request đặt cùng ghế đồng thời: đúng một request thành công (20 request thật vào container: 1 thành công, 19 `SEAT_TAKEN`).
- [x] Cập nhật README này và `docs/MIGRATION_TRACKER.md`; không commit `.env`, `*.db`, `__pycache__/`.
- [ ] PR vào `develop`, có 1 người khác duyệt (không tự merge).

Đã kiểm tra với cả 6 service Python chạy thật, trên uvicorn local và trên container Docker: `tests/integration/run_tests.py` đạt 54/54, 5 kịch bản `--expect-down` đạt hết. Chưa kiểm tra: JWT từ đầu đến cuối (User chưa cấp JWT thật, chỉ test bằng token tự ký) và giao diện Client/Admin trên trình duyệt.

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

Đã xử lý trong phạm vi service, cần nhóm trưởng xác nhận lại:

- **D-04:** `transactionId` luôn là chuỗi; Booking đọc được cả khi Payment trả id số hay chuỗi.
- **D-07:** `app/core/http.py` theo mẫu của User/Movie, kèm header `Allow` đầy đủ cho 405.
- **D-10:** giao dịch `BEGIN IMMEDIATE`, không đổi schema (xem §7).
- **D-11:** dùng `httpx.AsyncClient` như Showtime.
- **Múi giờ:** dùng `APP_TIMEZONE` thay giờ máy (xem mục sai khác bên dưới).
- **IPv4:** vẫn ưu tiên IPv4 như mã cũ. Đo trên Windows với URL `localhost`: giữ ghế 54 ms khi ép IPv4, 840 ms khi không ép.

Còn chờ quyết định: D-01, D-16 (migration dữ liệu thật), **D-18** (thời điểm bật JWT, quyền của `pay`/`cancel`, và cách Booking hỏi lại `GET /api/payment?bookingId=` khi endpoint đó chỉ cho `ADMIN`).

Danh sách đầy đủ và trạng thái: [OPEN_QUESTIONS.md](../docs/OPEN_QUESTIONS.md).

### Sai khác có chủ đích so với mã C# cũ

Mọi path, method, tên trường, mã HTTP và mã lỗi giữ nguyên. Các điểm dưới đây chỉ khác ở những tình huống mã cũ xử lý chưa đúng:

| Tình huống | Mã C# cũ | Bản Python | Lý do |
|---|---|---|---|
| Giờ hệ thống | Giờ máy chạy Booking | Theo `APP_TIMEZONE` | Container Python chạy UTC, giờ máy sẽ lệch 7 tiếng so với giờ chiếu và trình duyệt |
| Khách trả tiền xong nhưng ghế đã bán cho người khác | Vẫn gửi thông báo "Đặt vé thành công" | `notification: SKIPPED` | Đơn không còn hiệu lực, ghi log cần hoàn tiền như cũ |
| Hai yêu cầu `/pay` song song cho cùng đơn | Gửi 2 thông báo, ghi log nhầm "cần hoàn tiền" | Chỉ gửi 1 thông báo, không ghi log nhầm | Yêu cầu thứ hai nhận ra đơn đã `PAID` |
| Showtime trả thiếu `price`/`movieId` | 500 | 502 `SHOWTIME_SERVICE_ERROR` | Lỗi của đối tác, đúng nhóm mã trong hợp đồng |
| Id đơn vượt `INT` trên đường dẫn | 500 | 404 `NOT_FOUND` | Mã cũ tràn số khi parse |
| Chế độ `BOOKING_STORE=memory` | Có | Bỏ | Test dùng SQLite tạm |
