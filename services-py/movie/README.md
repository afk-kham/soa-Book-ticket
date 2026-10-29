# TV1 — Movie Service (Python / FastAPI / SQLite) — cổng 5001

> **Trạng thái: KHUNG.** Service chỉ khởi động và trả `GET /health`. Mọi nghiệp vụ do **TV1** viết theo README này.
> Nhánh làm việc: `feature/tv1-movie` (không làm trực tiếp trên `main`/`develop`). Đọc trước: [README chung](../README.md), [API_CONTRACT.md](../API_CONTRACT.md) §2, [ARCHITECTURE](../docs/ARCHITECTURE.md), [OPEN_QUESTIONS](../docs/OPEN_QUESTIONS.md).

## 1. Mục tiêu và phạm vi trách nhiệm

Quản lý danh mục phim. Cung cấp dữ liệu phim cho Client, Admin, Booking và được Showtime gọi để xác thực `movieId`.

Bạn **chỉ** sở hữu: `services-py/movie/`, `database/movie/` (schema/seed cũ — chỉ đọc), `docs/tv1-movie/` (tài liệu). Không sửa service khác, Admin, Client, hợp đồng chung.

## 2. API và nghiệp vụ đã xác minh từ source

Bảng đầy đủ (request/response/mã HTTP/lỗi) ở [API_CONTRACT.md](../API_CONTRACT.md) mục 2. Quy tắc phải giữ nguyên (đọc từ `services/movie/` — mã cũ là nguồn đối chiếu):

- Trường phim: `id, title, genre, duration, poster, createdAt` — **không đổi tên trường**.
- `POST`: `title` bắt buộc (không rỗng); `duration` nếu có phải là số nguyên > 0; trả 201 + phim vừa tạo.
- `PUT`: code cũ **cập nhật một phần** (chỉ trường được gửi) — contract ghi "đủ 4 trường" (D-08, chưa chốt).
- `DELETE` trả `{id, deleted:true}`; id không có → 404 `NOT_FOUND`.
- Danh sách sắp theo `id` tăng; danh sách rỗng là `[]`, không phải 404.
- `createdAt` dạng `"YYYY-MM-DD HH:MM:SS"`.

Ngoài bảng này **không thêm endpoint nào** nếu chưa có PR sửa `API_CONTRACT.md` được duyệt.

## 3. Cây thư mục và chức năng từng file

```
movie/
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

| File cũ trong `services/movie/` (giữ nguyên, chỉ đọc) | Chuyển sang |
|---|---|
| `movie_service.py` | route + validate + gửi response → `api/router.py`, `controllers/`, `services/`, `schemas/` |
| `database.py` | SQL → `repositories/`, kết nối → `db/` |
| `config.py` | đọc `.env`/biến môi trường → `core/config.py` |

## 4. File bạn được phép sửa

- Toàn bộ `services-py/movie/app/**` và `services-py/movie/tests/**`.
- `services-py/movie/requirements*.txt` (thêm dependency thật sự cần, pin phiên bản, ghi lý do trong PR).
- `services-py/movie/.env.example`, `Dockerfile`, `README.md` — nhưng **giữ nguyên cổng 5001, tên biến, tên file DB**.
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

- Một file `movie.db`, **chỉ service này** mở. Local: `./data/movie.db`; Docker: `/data/movie.db` (volume `movie_data`). `*.db` bị `.gitignore` — **không commit**.
- Schema cũ (MySQL) để **đối chiếu**: `movies(id INT AUTO_INCREMENT PK, title VARCHAR(255) NOT NULL, genre VARCHAR(100) NULL, duration INT NULL, poster VARCHAR(255) NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)`.
- Seed cũ: `database/movie/seed.sql`. **Không chạy** các file `schema.sql`/`seed.sql`/`seed.js` cũ (có `DROP`/`DELETE`/`drop()`).
- Khi viết schema SQLite: `CREATE TABLE IF NOT EXISTS`, idempotent, **không `DROP`**, không tự nạp dữ liệu lúc import/khởi động; giữ nguyên id và giá trị seed cũ (thêm dữ liệu mới = id lớn hơn).
- Việc tạo schema và nạp dữ liệu là bước **tường minh** (script/lệnh), chỉ làm sau khi nhóm chốt D-01, D-03, D-16. Chuyển dữ liệu thật từ nguồn cũ là **migration riêng**: sao lưu trước, đối chiếu sau (xem `docs/MIGRATION_TRACKER.md` §3).
- Test dùng DB tạm (`tmp_path`), **không** dùng file dữ liệu thật; không test hành vi xóa trên dữ liệu thật.

## 8. Dependency với service khác

- **Service này gọi:** Không gọi service nào.
- **Được gọi bởi:** Showtime (`GET /api/movies/{id}`, `GET /api/movies`), Booking (`GET /api/movies/{id}`), Client, Admin.
- Chỉ qua **HTTP + JSON** theo hợp đồng; không import code, không đọc DB của nhau. Mọi lời gọi ra ngoài phải có timeout và xử lý lỗi theo bảng `docs/ARCHITECTURE.md` §4.4.

## 9. Hợp đồng request/response phải tuân thủ

Đúng như [API_CONTRACT.md](../API_CONTRACT.md) §1 (quy ước chung) và §2: envelope `{"status":"success","data":…}` / `{"status":"error","code","message"}`, JSON camelCase, tiền là số nguyên VND, thời gian đúng định dạng của service, message lỗi tiếng Việt, không lộ lỗi SQL/stack. **Không tự đổi** path, method, tên trường, mã HTTP, mã lỗi. Phát hiện sai khác với code cũ → ghi vào PR/Issue, không "sửa cho đẹp".

## 10. Cổng, biến môi trường, URL nội bộ

| Biến | Giá trị khi chạy local | Giá trị trong Docker Compose | Ý nghĩa |
|---|---|---|---|
| `HOST` | `0.0.0.0` | `0.0.0.0` | Địa chỉ lắng nghe |
| `PORT` | `5001` | `5001` | Cổng trong container/tiến trình — **không đổi** (theo hợp đồng) |
| `DB_PATH` | `./data/movie.db` | `/data/movie.db` | File SQLite **riêng** của service |
| `JWT_SECRET` | `(trống)` | `${JWT_SECRET:-}` | Khóa JWT HS256 **dùng chung cả nhóm** (>= 32 ký tự, UTF-8 thô). Để trống trong khung; điền ở máy mình, **không commit khóa thật** |

### Thư viện đã khai báo trong `requirements.txt` (pin cố định)

| Gói | Phiên bản | Dùng cho |
|---|---|---|
| `fastapi` | 0.162.0 | Web framework (khung) |
| `uvicorn` | 0.54.0 | Chạy ứng dụng (khung) |
| `PyJWT` | 2.15.1 | Verify JWT cho `POST/PUT/DELETE` (cuối kỳ cần role `ADMIN`) |

Không thêm gói khác khi chưa cần; thêm bằng PR, **pin phiên bản**, nói rõ lý do (D-11). `sqlite3` là thư viện chuẩn của Python nên không cần cài. Sau khi sửa `requirements.txt` phải build lại image (`docker compose build movie`).

### Xác thực cuối kỳ (kế hoạch v2.1, mục 5) — áp dụng cho service này

- `GET /api/movies`, `GET /api/movies/{id}`: **công khai**.
- `POST/PUT/DELETE /api/movies`: **cuối kỳ** bắt buộc JWT role `ADMIN` (giữa kỳ công khai — code cũ hiện công khai).

Quy định JWT chung: **HS256**; khóa lấy từ biến môi trường `JWT_SECRET` (>= 32 ký tự, chuyển sang byte bằng **UTF-8 thô, không giải mã Base64**); claims `sub` (username), `userId`, `role` (`USER`/`ADMIN`), `iat`, `exp` (+2 giờ); gửi bằng `Authorization: Bearer <token>`; cho phép lệch giờ **60 giây**; thiếu/sai token → 401, đủ token nhưng thiếu quyền → 403; phải trả **204** cho `OPTIONS` (trình duyệt luôn gửi preflight khi có header `Authorization`). Khóa thật **không** được commit. Giữa kỳ các endpoint còn công khai — thời điểm bật xác thực do nhóm trưởng quyết (D-18).

- Cổng **5001** là cố định theo hợp đồng. Trong Compose, host publish `${MOVIE_HOST_PORT:-5001}` → container `5001`.
- URL gọi service khác **chỉ** được đọc từ `app/core/config.py` (nguồn: biến môi trường) — không hard-code trong lớp khác.

## 11. Chạy service và test

```bash
cd services-py/movie
python3.12 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                       # KHÔNG commit .env
uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
curl http://localhost:5001/health                        # {"status":"success","data":{"service":"movie-service","port":5001}}
python -m pytest -q                                        # test của service

# Docker (từ services-py/)
docker compose up --build movie
```

Test tích hợp liên service (`python tests/integration/run_tests.py`, thư mục gốc repo) chỉ dùng được khi các service liên quan đã được cài đặt đủ hành vi.

## 12. Checklist hoàn thành

- [ ] Đã đọc mã cũ `services/movie/` và ghi lại sai khác với contract (nếu có) vào PR.
- [ ] Mọi endpoint ở `API_CONTRACT.md` §2 đã cài đặt, khớp path/method/envelope/camelCase/mã HTTP/mã lỗi.
- [ ] Validation đủ (body rỗng, JSON sai, kiểu dữ liệu, giới hạn độ dài); không crash khi body rỗng/sai JSON.
- [ ] `/health`, `OPTIONS → 204`, CORS `*` đúng (sau khi nhóm chốt D-07).
- [ ] Schema SQLite idempotent, seed giữ nguyên id/giá trị; không có `DROP`.
- [ ] Không lộ trường nhạy cảm, lỗi SQL, stack trace.
- [ ] Test của service pass (DB tạm); `docker compose up --build movie` chạy và `/health` OK.
- [ ] Admin trang Phim và Client hiển thị phim bình thường khi trỏ về service Python (cổng 5001).
- [ ] Cập nhật README này và `docs/MIGRATION_TRACKER.md`; không commit `.env`, `*.db`, `__pycache__/`.
- [ ] PR vào `develop`, có 1 người khác duyệt (không tự merge).

## 13. File nặng — người dùng tự bổ sung / giữ nguyên

Khung **không tạo** và **không di chuyển** file nặng. Bảng cho biết nơi đặt và hiện trạng:

| Loại file | Vị trí đích / hiện có | Hiện có? | Việc cần làm (thủ công) |
|---|---|---|---|
| Sơ đồ ERD/DFD/UC | docs/tv1-movie/ | Có (`ERD_movie`, `DFD0/1/2_movie`, `UC_movie`) | Giữ nguyên; sơ đồ SQLite mới lưu tên mới cạnh file cũ |
| Báo cáo | docs/tv1-movie/ | Có (`05_baocao_movie.docx`, `baocao_movie.md`) | Giữ nguyên |
| Poster phim | `admin/assets/posters/`, `client/assets/posters/`, `client/img/posters/` | Có (15 JPG + 5 SVG) | Thêm file mới tên mới; không đổi tên file cũ |

Quy tắc chung (xem [ASSETS_GUIDE](../docs/ASSETS_GUIDE.md)): file cũ giữ nguyên tên và đường dẫn; file mới đặt tên mới cạnh file cũ; HTML đang tham chiếu ảnh nào thì không đổi đường dẫn ảnh đó.

## 14. Vấn đề chưa rõ — hỏi nhóm trưởng trước khi triển khai

- D-01 (SQLite), D-06 (thêm `/health`), D-07 (envelope/OPTIONS 204), D-08 (PUT một phần hay đủ 4 trường).
- Trường `poster`: là tên file (vd `poster1.jpg`) hay URL? Client xử lý cả hai — giữ nguyên giá trị seed, không validate chặt hơn code cũ khi chưa hỏi.

Danh sách đầy đủ và trạng thái: [OPEN_QUESTIONS.md](../docs/OPEN_QUESTIONS.md).
