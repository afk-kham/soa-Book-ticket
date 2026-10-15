# Showtime Service (TV2) — PHP · cổng 5002 · `showtime_db`

Suất chiếu và giá vé. PHP 8.1+ thuần, PDO (extension `pdo_mysql`), không framework.

```bash
cd services/showtime
cp .env.example .env                       # sửa DB_USER / DB_PASSWORD
php -S 0.0.0.0:5002 router.php             # http://localhost:5002
```
Khi `VALIDATE_MOVIE=true` (mặc định), POST/PUT có `movieId` sẽ gọi `GET {MOVIE_SERVICE_URL}/api/movies/{id}`;
Movie Service tắt → 503 `MOVIE_SERVICE_UNAVAILABLE`. Chạy riêng lẻ để thử: `VALIDATE_MOVIE=false`.

| Tệp | Vai trò |
|---|---|
| `router.php` | Điểm vào + định tuyến `/api/showtimes`, `/health` |
| `src/config.php` | Đọc `.env`, **không hard-code mật khẩu** |
| `src/db.php` | PDO + chuyển snake_case → camelCase |
| `src/validate.php` | Kiểm tra dữ liệu, gọi Movie Service |
| `src/response.php` | Envelope + CORS |

Tên cũ `movie_id` (query/body) vẫn được nhận; response luôn là `movieId`.

## Lịch chiếu tự xếp (`src/schedule.php`)
Mỗi lần `GET /api/showtimes`, service kiểm tra `AUTO_SCHEDULE_DAYS` ngày tới (mặc định 7); ngày nào **chưa có suất nào** thì xếp lịch: mỗi phim (lấy qua API Movie) chiếu ở 3 rạp, 2 suất/rạp, mỗi phim một phòng riêng; giá 75.000đ (trước 12h −10.000đ, từ 17h +10.000đ, cuối tuần +15.000đ). Không đụng suất đã có; xóa lẻ một suất cũng không bị sinh lại. Tắt: `AUTO_SCHEDULE_DAYS=0`. Múi giờ: `APP_TIMEZONE` (mặc định `Asia/Ho_Chi_Minh`).
`?upcoming=1` chỉ trả suất chưa bắt đầu.
