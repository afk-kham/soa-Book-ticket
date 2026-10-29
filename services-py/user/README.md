# TV3 — User/Auth Service (Python / FastAPI / SQLite) — cổng 5003

> **Trạng thái: KHUNG.** Service chỉ khởi động và trả `GET /health`. Mọi nghiệp vụ do **TV3** viết theo README này.
> Nhánh làm việc: `feature/tv3-user` (không làm trực tiếp trên `main`/`develop`). Đọc trước: [README chung](../README.md), [API_CONTRACT.md](../API_CONTRACT.md) §4, [ARCHITECTURE](../docs/ARCHITECTURE.md), [OPEN_QUESTIONS](../docs/OPEN_QUESTIONS.md).

## 1. Mục tiêu và phạm vi trách nhiệm

Đăng ký, đăng nhập, tra cứu người dùng. Booking gọi để xác minh người dùng tồn tại.

Bạn **chỉ** sở hữu: `services-py/user/`, `database/user/` (schema/seed cũ — chỉ đọc), `docs/tv3-user/` (tài liệu). Không sửa service khác, Admin, Client, hợp đồng chung.

## 2. API và nghiệp vụ đã xác minh từ source

Bảng đầy đủ (request/response/mã HTTP/lỗi) ở [API_CONTRACT.md](../API_CONTRACT.md) mục 4. Quy tắc phải giữ nguyên (đọc từ `services/user/` — mã cũ là nguồn đối chiếu):

- Endpoint trong contract: `POST /api/register`, `POST /api/login`, `GET /api/users` (+`?username=`), `GET /api/users/{id}`. **Không có PUT/DELETE** — chỉ thêm khi nhóm duyệt contract + chính sách xóa (ảnh hưởng booking/log).
- Đăng ký: `username` 3–50 ký tự `[A-Za-z0-9_.]`, `password` 6–72, `email` tùy chọn (≤ 100, hợp lệ); `role` **luôn `USER`**, bỏ qua `role` client gửi; trùng username → 409 `CONFLICT`.
- Đăng nhập: BCrypt (`$2a$`, cost 10); sai user và sai mật khẩu **cùng một thông báo** (401 `UNAUTHORIZED`); `token = "demo-token-<username>"` (giữa kỳ).
- **Không bao giờ** trả `passwordHash`; `GET /api/users?username=x` trả mảng 0/1 phần tử.
- Hash BCrypt trong seed (`admin/Admin@123`, `user1/User@123`, `user2/User@123`) phải đăng nhập được bằng thư viện Python — kiểm tra khi chọn thư viện (D-11).

Ngoài bảng này **không thêm endpoint nào** nếu chưa có PR sửa `API_CONTRACT.md` được duyệt.

## 3. Cây thư mục và chức năng từng file

```
user/
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

| File cũ trong `services/user/` (giữ nguyên, chỉ đọc) | Chuyển sang |
|---|---|
| `Main.java` | route + validate + login/register → `api/`, `controllers/`, `services/`, `schemas/` |
| `UserDao.java` | SQL → `repositories/`, `entities/` |
| `Config.java` | → `core/config.py` (đã có `JWT_SECRET`, chưa dùng) |
| `Http.java` | envelope + CORS → mẫu dùng chung (D-07) |

## 4. File bạn được phép sửa

- Toàn bộ `services-py/user/app/**` và `services-py/user/tests/**`.
- `services-py/user/requirements*.txt` (thêm dependency thật sự cần, pin phiên bản, ghi lý do trong PR).
- `services-py/user/.env.example`, `Dockerfile`, `README.md` — nhưng **giữ nguyên cổng 5003, tên biến, tên file DB**.
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

- Một file `user.db`, **chỉ service này** mở. Local: `./data/user.db`; Docker: `/data/user.db` (volume `user_data`). `*.db` bị `.gitignore` — **không commit**.
- Schema cũ (MySQL) để **đối chiếu**: `users(id INT AUTO_INCREMENT PK, username VARCHAR(50) NOT NULL UNIQUE, password_hash VARCHAR(100) NOT NULL, email VARCHAR(100) NULL, role VARCHAR(10) NOT NULL DEFAULT 'USER')`.
- Seed cũ: `database/user/seed.sql` (3 tài khoản mẫu). **Không chạy** các file `schema.sql`/`seed.sql`/`seed.js` cũ (có `DROP`/`DELETE`/`drop()`).
- Khi viết schema SQLite: `CREATE TABLE IF NOT EXISTS`, idempotent, **không `DROP`**, không tự nạp dữ liệu lúc import/khởi động; giữ nguyên id và giá trị seed cũ (thêm dữ liệu mới = id lớn hơn).
- Việc tạo schema và nạp dữ liệu là bước **tường minh** (script/lệnh), chỉ làm sau khi nhóm chốt D-01, D-03, D-16. Chuyển dữ liệu thật từ nguồn cũ là **migration riêng**: sao lưu trước, đối chiếu sau (xem `docs/MIGRATION_TRACKER.md` §3).
- Test dùng DB tạm (`tmp_path`), **không** dùng file dữ liệu thật; không test hành vi xóa trên dữ liệu thật.

## 8. Dependency với service khác

- **Service này gọi:** Không gọi service nào.
- **Được gọi bởi:** Booking (`GET /api/users?username=`), Client (đăng nhập/đăng ký), Admin (danh sách).
- Chỉ qua **HTTP + JSON** theo hợp đồng; không import code, không đọc DB của nhau. Mọi lời gọi ra ngoài phải có timeout và xử lý lỗi theo bảng `docs/ARCHITECTURE.md` §4.4.

## 9. Hợp đồng request/response phải tuân thủ

Đúng như [API_CONTRACT.md](../API_CONTRACT.md) §1 (quy ước chung) và §4: envelope `{"status":"success","data":…}` / `{"status":"error","code","message"}`, JSON camelCase, tiền là số nguyên VND, thời gian đúng định dạng của service, message lỗi tiếng Việt, không lộ lỗi SQL/stack. **Không tự đổi** path, method, tên trường, mã HTTP, mã lỗi. Phát hiện sai khác với code cũ → ghi vào PR/Issue, không "sửa cho đẹp".

## 10. Cổng, biến môi trường, URL nội bộ

| Biến | Giá trị khi chạy local | Giá trị trong Docker Compose | Ý nghĩa |
|---|---|---|---|
| `HOST` | `0.0.0.0` | `0.0.0.0` | Địa chỉ lắng nghe |
| `PORT` | `5003` | `5003` | Cổng trong container/tiến trình — **không đổi** (theo hợp đồng) |
| `DB_PATH` | `./data/user.db` | `/data/user.db` | File SQLite **riêng** của service |
| `JWT_SECRET` | `(trống)` | `${JWT_SECRET:-}` | Khóa JWT HS256 **dùng chung cả nhóm** (>= 32 ký tự, UTF-8 thô). Để trống trong khung; điền ở máy mình, **không commit khóa thật** |

### Thư viện đã khai báo trong `requirements.txt` (pin cố định)

| Gói | Phiên bản | Dùng cho |
|---|---|---|
| `fastapi` | 0.162.0 | Web framework (khung) |
| `uvicorn` | 0.54.0 | Chạy ứng dụng (khung) |
| `PyJWT` | 2.15.1 | **Cấp** JWT khi đăng nhập và verify cho `GET /api/users` |
| `bcrypt` | 5.0.0 | Kiểm tra/tạo hash BCrypt. **Đã thử:** đọc được hash `$2a$` của `admin`/`user1` trong Phụ lục A |

Không thêm gói khác khi chưa cần; thêm bằng PR, **pin phiên bản**, nói rõ lý do (D-11). `sqlite3` là thư viện chuẩn của Python nên không cần cài. Sau khi sửa `requirements.txt` phải build lại image (`docker compose build user`).

### Xác thực cuối kỳ (kế hoạch v2.1, mục 5) — áp dụng cho service này

- `POST /api/login`: **công khai**; giữa kỳ trả thông tin user, **cuối kỳ trả JWT**.
- `GET /api/users`: **cuối kỳ** role `ADMIN`.
- `POST /api/register` **không có trong bảng phân quyền v2.1** (repo hiện có) — hỏi nhóm trưởng về quyền truy cập.

Quy định JWT chung: **HS256**; khóa lấy từ biến môi trường `JWT_SECRET` (>= 32 ký tự, chuyển sang byte bằng **UTF-8 thô, không giải mã Base64**); claims `sub` (username), `userId`, `role` (`USER`/`ADMIN`), `iat`, `exp` (+2 giờ); gửi bằng `Authorization: Bearer <token>`; cho phép lệch giờ **60 giây**; thiếu/sai token → 401, đủ token nhưng thiếu quyền → 403; phải trả **204** cho `OPTIONS` (trình duyệt luôn gửi preflight khi có header `Authorization`). Khóa thật **không** được commit. Giữa kỳ các endpoint còn công khai — thời điểm bật xác thực do nhóm trưởng quyết (D-18).

- Cổng **5003** là cố định theo hợp đồng. Trong Compose, host publish `${USER_HOST_PORT:-5003}` → container `5003`.
- URL gọi service khác **chỉ** được đọc từ `app/core/config.py` (nguồn: biến môi trường) — không hard-code trong lớp khác.

## 11. Chạy service và test

```bash
cd services-py/user
python3.12 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                       # KHÔNG commit .env
uvicorn app.main:app --host 0.0.0.0 --port 5003 --reload
curl http://localhost:5003/health                        # {"status":"success","data":{"service":"user-service","port":5003}}
python -m pytest -q                                        # test của service

# Docker (từ services-py/)
docker compose up --build user
```

Test tích hợp liên service (`python tests/integration/run_tests.py`, thư mục gốc repo) chỉ dùng được khi các service liên quan đã được cài đặt đủ hành vi.

## 12. Checklist hoàn thành

- [ ] Đã đọc mã cũ `services/user/` và ghi lại sai khác với contract (nếu có) vào PR.
- [ ] Mọi endpoint ở `API_CONTRACT.md` §4 đã cài đặt, khớp path/method/envelope/camelCase/mã HTTP/mã lỗi.
- [ ] Validation đủ (body rỗng, JSON sai, kiểu dữ liệu, giới hạn độ dài); không crash khi body rỗng/sai JSON.
- [ ] `/health`, `OPTIONS → 204`, CORS `*` đúng (sau khi nhóm chốt D-07).
- [ ] Schema SQLite idempotent, seed giữ nguyên id/giá trị; không có `DROP`.
- [ ] Không lộ trường nhạy cảm, lỗi SQL, stack trace.
- [ ] Test của service pass (DB tạm); `docker compose up --build user` chạy và `/health` OK.
- [ ] Không có chỗ nào log hoặc trả `password_hash`/mật khẩu.
- [ ] Đăng nhập được 3 tài khoản mẫu bằng hash BCrypt có sẵn.
- [ ] Cập nhật README này và `docs/MIGRATION_TRACKER.md`; không commit `.env`, `*.db`, `__pycache__/`.
- [ ] PR vào `develop`, có 1 người khác duyệt (không tự merge).

## 13. File nặng — người dùng tự bổ sung / giữ nguyên

Khung **không tạo** và **không di chuyển** file nặng. Bảng cho biết nơi đặt và hiện trạng:

| Loại file | Vị trí đích / hiện có | Hiện có? | Việc cần làm (thủ công) |
|---|---|---|---|
| Sơ đồ ERD/DFD/UC | docs/tv3-user/ | Có (`ERD/DFD0/DFD1/UC_user`; `DFD2_user` **chỉ có `.drawio`, chưa có `.png`**) | Giữ nguyên; tự xuất `DFD2_user.png` bằng draw.io nếu cần |
| Báo cáo | docs/tv3-user/ | Có (`05_baocao_user.docx`) | Giữ nguyên |

Quy tắc chung (xem [ASSETS_GUIDE](../docs/ASSETS_GUIDE.md)): file cũ giữ nguyên tên và đường dẫn; file mới đặt tên mới cạnh file cũ; HTML đang tham chiếu ảnh nào thì không đổi đường dẫn ảnh đó.

## 14. Vấn đề chưa rõ — hỏi nhóm trưởng trước khi triển khai

- D-01, D-06 (`/health`), D-07, D-11 (`bcrypt`), D-18 (JWT/xác thực).
- `database/user/schema.sql` có `DROP DATABASE IF EXISTS user_db` — **tuyệt đối không chạy**; schema SQLite phải dùng `CREATE TABLE IF NOT EXISTS`.
- Ràng buộc UNIQUE `username` ở mức DB phải giữ để chống đăng ký đồng thời (code cũ bắt SQLState 23000 → 409).

Danh sách đầy đủ và trạng thái: [OPEN_QUESTIONS.md](../docs/OPEN_QUESTIONS.md).
