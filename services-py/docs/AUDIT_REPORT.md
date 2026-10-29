# AUDIT_REPORT — Kết quả kiểm tra repository và `python_migration_docs.zip`

Phạm vi đã đọc (thật sự mở và đọc, không suy đoán từ tên thư mục):

- Repo `https://github.com/afk-kham/soa-Book-ticket`, nhánh `main` @ `326602e` (clone chỉ-đọc), 293 file được theo dõi, 7 commit.
- Mã nguồn đủ 6 service, schema/seed `database/*`, `API_CONTRACT.md`, `ARCHITECTURE.md`, `DATABASE_CONTRACT.md`, `INTEGRATION_FLOW.md`, `INTEGRATION_CHECKLIST.md`, `TEAM_RULES.md`, `CHANGELOG.md`, `README.md`, `.env.example`, `.gitignore`, `scripts/start-all.sh`, `admin/js/config.js`, `client/js/config.js`, `.github/pull_request_template.md`, đầu `ui-seed/seed-movies.py`.
- ZIP: 19 mục (README_PHAN_CONG, README_MIGRATION, 6 README thành viên, 8 prompt) — đọc đầy đủ README_PHAN_CONG, README_MIGRATION, README TV1 & TV4, prompt 00/01/TV1 và phần "Nhiệm vụ/Ràng buộc riêng" của TV2/3/5/6.

**Đã đọc thêm (sau lần audit đầu, theo yêu cầu của chủ dự án):** `docs/tai-lieu/Ke_Hoach_Trien_Khai_SOA_Dat_Ve_Phim_v2_1.docx` (kế hoạch v2.1, 02/10/2026) — kết quả ở M12–M14 bên dưới.

**Chưa đọc / chưa kiểm chứng** (nói rõ để không tuyên bố quá mức): nội dung các `.docx/.pdf/.drawio/.png` còn lại, kể cả `Phieu_Giao_Viec_Chuan_Bi_Giua_Ky.docx` (không mở file nặng theo quy định); `tests/integration/run_tests.py` chỉ xem lướt (không phân tích từng ca); `services/*/README.md`, `docs/tv*/baocao_*.md`, `docs/REVIEW_CAI_TIEN_DAT_VE.md`, `services/notification/docs/*`, `docs/tv4-booking/source-giua-ky/*` chưa đọc; `services/booking/BookingStore.cs` và `database/*/seed.sql` chỉ đọc phần liên quan; **chưa chạy** bất kỳ service cũ nào.

## 1. Kiểm kê service hiện có

| Service | TV | Ngôn ngữ / framework (code thật) | Entry point | Cổng | CSDL (thật) | Dependency chính |
|---|---|---|---|---:|---|---|
| Movie | TV1 | Python 3.10+, `http.server` thuần | `movie_service.py` | 5001 | MySQL `movie_db`, bảng `movies` | `pymysql`, `cryptography` |
| Showtime | TV2 | PHP 8.1+ thuần, PDO | `router.php` (`php -S`) | 5002 | MySQL `showtime_db`, bảng `showtimes` | `pdo_mysql` |
| User | TV3 | Java 17, `com.sun.net.httpserver`, JDBC | `userservice.Main` | 5003 | MySQL `user_db`, bảng `users` | `mysql-connector-j 8.4.0`, `jbcrypt 0.4`, `gson 2.10.1` |
| Booking | TV4 | C# .NET 8, `HttpListener` | `Program.cs` | 5004 | MySQL `booking_db`, bảng `bookings` (hoặc `BOOKING_STORE=memory` khi test) | ADO.NET MySQL |
| Payment | TV5 | Node.js ≥ 18, `http` | `payment_service.js` | 5005 | **MongoDB** `payment_db`, collection `transactions` | `mongodb ^6.10.0` |
| Notification | TV6 | Go 1.21+, `net/http` | `main.go` | 5006 | MySQL `notification_db`, bảng `notification_logs` | `database/sql` |
| Admin | Nhóm trưởng | HTML/CSS/JS tĩnh | `admin/index.html` | 8081 | — | — |
| Client | Nhóm trưởng | HTML/CSS/JS tĩnh | `client/index.html` | 8080 | — | — |

Chạy hiện tại: từng tiến trình riêng bằng `scripts/start-all.sh|bat` (không có Dockerfile/Compose nào cho hệ thống chính; chỉ có `docs/tv4-booking/source-giua-ky/docker-compose.yml` là tài liệu tham khảo của bản giữa kỳ Booking).

## 2. Endpoint đã xác minh từ source

Chi tiết từng endpoint (request/response/mã HTTP/lỗi) ở [`../API_CONTRACT.md`](../API_CONTRACT.md). Tóm tắt số lượng: Movie 5, Showtime 6 (gồm `/health`), User 4, Booking 8 (gồm `/health`), Payment 3 (gồm `/health`), Notification 6 (không có `/health`).

## 3. Database thật, schema, kết nối

| Service | Loại | Schema (tóm tắt) | Cách kết nối | Nơi lưu dữ liệu |
|---|---|---|---|---|
| Movie | MySQL | `movies(id AI PK, title NN, genre, duration, poster, created_at)` | PyMySQL, `DB_HOST/PORT/NAME/USER/PASSWORD`, autocommit | Máy chủ MySQL |
| Showtime | MySQL | `showtimes(id AI PK, movie_id NN, cinema, room, time DATETIME, price)` — không FK | PDO | Máy chủ MySQL |
| User | MySQL | `users(id AI, username UNIQUE, password_hash NN (BCrypt `$2a$`), email, role DEFAULT 'USER')` | JDBC (`DB_URL` ghi đè được) | Máy chủ MySQL |
| Booking | MySQL | `bookings(id AI, movie_id, showtime_id, username, seats 'A1,A2', total_price, status CHECK, created_at)` + 2 index + 2 CHECK | ADO.NET | Máy chủ MySQL |
| Payment | MongoDB | `transactions{_id ObjectId, bookingId, amount, method, status, paidAt}`, index `bookingId` | driver `mongodb` (`MONGO_URI`, `MONGO_DB`) | Máy chủ MongoDB |
| Notification | MySQL | `notification_logs(id AI, booking_id, username, channel, message, sent_at)` + index `(sent_at,id)` | `database/sql` | Máy chủ MySQL |

Nguy cơ mất dữ liệu cần lưu ý: `database/movie|showtime|booking/schema.sql` có `DROP TABLE IF EXISTS`, `database/user/schema.sql` có **`DROP DATABASE IF EXISTS user_db`**, các `seed.sql` có `DELETE FROM`, `database/payment/seed.js` có `db.transactions.drop()`. **Không chạy các file này trên dữ liệu thật; khung này không chạy chúng.**

## 4. Ai gọi ai (xác minh từ code)

| Caller → Callee | Đường dẫn | Timeout | Khi callee lỗi |
|---|---|---|---|
| Booking → User | `GET /api/users?username=` | 5s | 503 `USER_SERVICE_UNAVAILABLE` / 502 `USER_SERVICE_ERROR`; 404 `USER_NOT_FOUND` |
| Booking → Movie | `GET /api/movies/{id}` | 5s | 404 `MOVIE_NOT_FOUND`; 503/502 |
| Booking → Showtime | `GET /api/showtimes/{id}` (lấy `price`, `movieId`, `time`) | 5s | 404 `SHOWTIME_NOT_FOUND`; 503/502; 400 `SHOWTIME_CLOSED` |
| Booking → Payment | `POST /api/payment`; hỏi lại `GET /api/payment?bookingId=` | 5s; hỏi lại 2s | 503 `PAYMENT_SERVICE_UNAVAILABLE`; 409 xử lý như đã trả |
| Booking → Notification | `POST /api/notify` (`channel=EMAIL`) | 3s | Bỏ qua lỗi, `notification: FAILED` |
| Showtime → Movie | `GET /api/movies/{id}` (POST/PUT) và `GET /api/movies` (xếp lịch) | 3s | 400 `MOVIE_NOT_FOUND`; 503 `MOVIE_SERVICE_UNAVAILABLE`; xếp lịch: dùng các `movie_id` đã có |
| Client → Movie, Showtime, User, Booking | trực tiếp từ trình duyệt | — | — |
| Admin → cả 6 service | trực tiếp từ trình duyệt (dò sống bằng `/api/movies`, `/api/showtimes`, `/api/users`, `/health` của Booking, `/api/payment`, `/api/notify/logs`) | — | — |

## 5. Frontend, tài nguyên, tài liệu (phải giữ nguyên)

| Khu vực | Nội dung | Trạng thái trong khung |
|---|---|---|
| `admin/` | `index.html`, `css/admin.css`, `js/{common,config,movie-extras}.js`, `pages/*.html` (6 trang), `assets/posters|backdrops/*.jpg` | **Không đụng** |
| `client/` | `index.html`, `css/client.css`, `js/{app,barcode,config,movie-extras,qr}.js`, `assets/*.jpg`, `img/posters/*.svg` | **Không đụng** |
| `docs/` | ERD/DFD/UC (`.drawio`, `.png`, `.mmd`), báo cáo (`.docx`, `.pdf`, `.md`), `anh-ket-qua/*.png`, `source-giua-ky/` (C#) | **Không đụng** |
| `design/figma-plugin/` | `code.js`, `manifest.json`, README | **Không đụng** |
| Gốc repo | 16 ảnh chụp màn hình `admin_*.png`, `client_*.png`, `test_before_client_1440.png` (nằm lẻ ở thư mục gốc) | **Không đụng**; đề xuất gom vào `docs/screenshots/` — làm thủ công (xem `ASSETS_GUIDE.md`) |
| `scripts/`, `tests/integration/`, `ui-seed/` | Script khởi động/MySQL, test tích hợp, seed qua API | **Không đụng** (vẫn trỏ tới service cũ) |

Repo có 147 file ảnh/tài liệu nặng (`png/jpg/jpeg/svg/docx/pdf/drawio`), `.git` ≈ 19 MB. Gói khung **không chứa file nhị phân nào**.

## 6. Đối chiếu ZIP ↔ repo: mâu thuẫn và điểm cần nhóm biết

| # | Nội dung | Chi tiết (sự thật trong source ưu tiên) |
|---|---|---|
| M1 | **"Tiếp tục dùng SQLite hiện có"** | Không có SQLite nào trong repo. `git grep -i sqlite` chỉ thấy dòng `db.sqlite3` trong `.gitignore`; không file `.db/.sqlite` nào được theo dõi. Thực tế: MySQL ×5 + MongoDB ×1. README_PHAN_CONG và README_MIGRATION của ZIP cũng cảnh báo điều này. **Quyết định mới của chủ dự án (trong yêu cầu dựng khung): toàn bộ dùng SQLite** → đây là *thay đổi công nghệ lưu trữ*, không phải "tiếp tục". Khung chuẩn bị theo SQLite; migration dữ liệu là việc riêng (D-01). |
| M2 | Triết lý đa ngôn ngữ | `ARCHITECTURE.md` §1: "6 ngôn ngữ khác nhau là có chủ đích" và §4 lộ trình cuối kỳ (Django, CodeIgniter 4, Spring Boot…). Quyết định mới (6× FastAPI) **mâu thuẫn** với hai đoạn này → nhóm trưởng cần cập nhật `ARCHITECTURE.md` (D-12). |
| M3 | Biến môi trường | `API_CONTRACT.md` §1 liệt kê `DB_HOST…DB_PASSWORD`, Payment `MONGO_URI/MONGO_DB`. SQLite dùng `DB_PATH` (D-05). |
| M4 | Nhánh tích hợp | ZIP: PR vào `develop`. Yêu cầu hiện tại: đưa khung lên `main`. `TEAM_RULES.md`: `main` chỉ nhận từ `develop`. Hơn nữa `develop` và `feature/tv1…tv5` đều ở `1e3fdd2` (**sau `main` 6 commit**), `feature/tv6-notification` ở `0a17120` (sau `main` 5 commit) → chưa nhánh nào có giao diện/Booking mới nhất (D-15). |
| M5 | Movie `PUT` | Contract: "Sửa (đủ 4 trường)". Code: cập nhật một phần (COALESCE) (D-08). |
| M6 | `/health` | Contract chỉ nêu cho Showtime, Booking, Payment. Movie, User, Notification **không có** `/health`. Khung thêm `/health` cho cả 6 (hạ tầng, phục vụ Docker healthcheck) — cần xác nhận (D-06). |
| M7 | Mã trạng thái Notification | Code: `POST /api/notify` → **200**, `POST /api/notify/logs` → **201**, GET/PUT/DELETE → 200. Contract không nêu mã cho các endpoint này (D-13). |
| M8 | `payment.id` | Payment trả `id` là **chuỗi** (ObjectId); Booking đọc `id` bằng `GetString()`. Nếu SQLite dùng số nguyên → Booking hỏng (D-04). |
| M9 | Mã lỗi `NOT_FOUND` vs `*_NOT_FOUND` | Movie/Showtime/User tự trả `NOT_FOUND`; chỉ Booking trả `USER_NOT_FOUND`, `MOVIE_NOT_FOUND`, `SHOWTIME_NOT_FOUND` (và Showtime trả `MOVIE_NOT_FOUND` khi POST sai phim). Khớp bảng contract §1 nhưng cần chú ý khi viết handler. |
| M10 | Nhãn công nghệ ở Admin | `admin/js/config.js` ghi cứng `tech`/`db` ("Python", "MySQL", "Go"…). Sau migration các nhãn này lỗi thời; Admin thuộc nhóm trưởng và **không bị sửa** ở giai đoạn này (D-14). |
| M11 | Test/scripts | `scripts/*`, `tests/integration/run_tests.py`, `ui-seed/seed-movies.py` giả định service cũ + MySQL/Mongo. Không bị sửa. |
| M12 | **Kế hoạch v2.1 chốt framework theo từng ngôn ngữ** | Python → **Django** ở cuối kỳ; ghi rõ "fast API" **không phải** thư viện FastAPI; "không ai bị làm lại theo FastAPI/Django". Dùng FastAPI cho cả 6 service là quyết định của nhóm, **chưa được giảng viên xác nhận** (D-19). v2.1 nêu 5 service cùng ngôn ngữ hoặc khác ngôn ngữ đều được cộng điểm. |
| M13 | **JWT/ADMIN/`X-Internal-Key` bắt buộc cuối kỳ** | v2.1 §5: JWT HS256, claims `sub/userId/role/iat/exp(2h)`, khóa UTF-8 thô, lệch 60s; ADMIN cho ghi Movie/Showtime, `GET /users`, `GET /booking`, `GET /payment`, `GET /notify/logs`; `X-Internal-Key` cho `POST /notify`. Code repo hiện **chưa có JWT**. Khung đã thêm `PyJWT` + `JWT_SECRET`/`INTERNAL_KEY` (D-11, D-18). |
| M14 | Endpoint repo có nhưng v2.1 không liệt kê | `register`, `booking pay/cancel/seats/availability`, `notify/logs` POST/PUT/DELETE — chưa có quy tắc phân quyền (D-18). Payment `GET` chỉ ADMIN trong v2.1 xung đột với việc Booking hỏi lại `GET /api/payment?bookingId=` (D-18c). Seed Phụ lục A khớp `database/*/seed.*` (đã đối chiếu id/giá trị chính). |

## 7. Bảng mapping cấu trúc hiện tại → cấu trúc mục tiêu

| Hiện tại (giữ nguyên, chỉ đọc) | Mục tiêu mới (thêm vào, không ghi đè) | Ghi chú |
|---|---|---|
| `services/movie/{movie_service.py, config.py, database.py}` | `services-py/movie/app/{api,controllers,services,repositories,entities,schemas,db,core}` | `movie_service.py` (route+validate) → api/controllers/services; `database.py` → repositories + db; `config.py` → core/config.py |
| `services/showtime/{router.php, src/config.php, db.php, validate.php, schedule.php, response.php}` | `services-py/showtime/app/…` | `schedule.php` → services (xếp lịch); `validate.php` → schemas/services; `db.php` → repositories |
| `services/user/src/main/java/userservice/{Main,Config,Http,UserDao}.java` | `services-py/user/app/…` | `UserDao` → repositories; `Main` → api/controllers/services |
| `services/booking/{Program,BookingStore,Upstream,Models,Config}.cs` | `services-py/booking/app/…` | `Upstream.cs` → client HTTP trong services; `BookingStore.cs` → repositories |
| `services/payment/payment_service.js` | `services-py/payment/app/…` | |
| `services/notification/{main,handler,store,notification,model,config,middleware,response}.go` | `services-py/notification/app/…` | `handler.go` → api/controllers; `store.go` → repositories |
| `services/*/.env.example`, `README.md`, `requirements.txt` | `services-py/*/.env.example`, `README.md`, `requirements.txt` | Tên trùng nên **phải** nằm thư mục khác |
| `database/<svc>/schema.sql + seed.sql`, `seed.js` | *(chưa tạo)* | Viết lại cho SQLite trong giai đoạn migration, giữ nguyên id/giá trị seed |
| `API_CONTRACT.md` (gốc) | `services-py/API_CONTRACT.md` | Bảng đối chiếu; gốc vẫn là nguồn sự thật |
| `README.md` (gốc) | `services-py/README.md` | README của bộ khung |
| `.env.example` (gốc) | `services-py/.env.example` | Biến cho Compose |
| *(không có)* | `services-py/docker-compose.yml`, `*/Dockerfile` | Mới |

## 8. Rủi ro chính

1. **Đổi CSDL + đổi ngôn ngữ cùng lúc** (6 service): rủi ro hồi quy cao → làm từng service, đối chiếu với bảng ở `MIGRATION_TRACKER.md`, giữ service cũ chạy song song cho tới khi hết lệch.
2. **Tương thích hợp đồng:** FastAPI mặc định trả 422 / `{"detail":…}` / preflight 200 → phải ghi đè để khớp envelope và OPTIONS 204 (D-07).
3. **Đồng thời với SQLite:** Showtime dùng `GET_LOCK` của MySQL; Booking dùng khóa trong tiến trình; SQLite chỉ một writer → cần thiết kế (D-09, D-10).
4. **Mất dữ liệu / ghi đè seed:** tuyệt đối không chạy `schema.sql`/`seed.sql` cũ; seed SQLite phải idempotent và giữ id.
5. **Nhánh cũ:** `develop`/`feature/*` chưa có commit mới nhất của `main` (D-15).
6. **Chưa kiểm chứng Docker:** image chưa build được trong môi trường dựng khung.
