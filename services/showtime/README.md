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
