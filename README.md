# 🎬 SOA — Hệ thống đặt vé phim

Đồ án môn **Kiến trúc hướng dịch vụ (SOA)**. Hệ thống gồm **6 service độc lập** (6 ngôn ngữ, 6 CSDL, 6 cổng),
giao tiếp với nhau **chỉ bằng HTTP + JSON**, cùng **Admin** dùng chung một khung giao diện và **Client** cho người dùng cuối.
Đây **không phải** một ứng dụng nguyên khối: tắt một service, các service còn lại vẫn chạy.

| Service | Cổng | Công nghệ | CSDL | Phụ trách |
|---|---|---|---|---|
| [Movie](services/movie) | 5001 | Python | `movie_db` (MySQL) | TV1 |
| [Showtime](services/showtime) | 5002 | PHP | `showtime_db` (MySQL) | TV2 |
| [User](services/user) | 5003 | Java | `user_db` (MySQL) | TV3 |
| [Booking](services/booking) | 5004 | C# (.NET 8) | `booking_db` (MySQL) | TV4 |
| [Payment](services/payment) | 5005 | Node.js | `payment_db` (MongoDB) | TV5 |
| [Notification](services/notification) | 5006 | Go | `notification_db` (MySQL) | TV6 |
| [Admin](admin) | 8081 | HTML/CSS/JS | — | Nhóm trưởng |
| [Client](client) | 8080 | HTML/CSS/JS | — | Nhóm trưởng |

## Đọc theo thứ tự này
1. [`ARCHITECTURE.md`](ARCHITECTURE.md) — kiến trúc và nguyên tắc bắt buộc
2. [`API_CONTRACT.md`](API_CONTRACT.md) — **hợp đồng API chung** (mọi người phải theo)
3. [`DATABASE_CONTRACT.md`](DATABASE_CONTRACT.md) — mỗi service một CSDL, seed dùng chung
4. [`INTEGRATION_FLOW.md`](INTEGRATION_FLOW.md) — luồng đặt vé, xử lý khi service sập
5. [`TEAM_RULES.md`](TEAM_RULES.md) — ai sửa gì, quy trình Git
6. [`INTEGRATION_CHECKLIST.md`](INTEGRATION_CHECKLIST.md) — kiểm tra trước khi gộp/demo · [`CHANGELOG.md`](CHANGELOG.md)

## Chạy toàn bộ hệ thống

**Yêu cầu:** MySQL 8 (hoặc MariaDB 10.6+), MongoDB, Python 3.10+, PHP 8.1+ (`pdo_mysql`), JDK 17+ & Maven, .NET SDK 8, Node.js 18+, Go 1.21+.

```bash
# 1) Tạo CSDL (MySQL phải đang chạy)
DB_USER=root DB_PASSWORD=<mật khẩu> bash scripts/init-db.sh        # Windows: scripts\init-db.bat

# 2) Mỗi service: sao chép .env.example thành .env và sửa DB_USER / DB_PASSWORD
for s in movie showtime user booking payment notification; do cp services/$s/.env.example services/$s/.env; done

# 3) Chạy tất cả (mỗi service một tiến trình)
bash scripts/start-all.sh                                           # Windows: scripts\start-all.bat

# 4) Kiểm tra
python3 tests/integration/run_tests.py
```
Mở **Client** http://localhost:8080 (đăng nhập `user1` / `User@123`) và **Admin** http://localhost:8081.
Dừng: `bash scripts/stop-all.sh`. Chạy từng service riêng: xem `README.md` trong thư mục service.

Demo chịu lỗi (cho buổi bảo vệ): tắt một service rồi chạy
`python3 tests/integration/run_tests.py --expect-down payment` (hoặc `notification`, `showtime`, `user`, `movie`).

## Cấu trúc thư mục
```
services/<tên>/   mã nguồn từng service (+ .env.example, README)
database/<tên>/   schema.sql + seed.sql (Payment: seed.js)
admin/            khung chung css/ js/ + pages/ cho 6 service
client/           ứng dụng người dùng cuối (+ assets/posters, assets/backdrops)
ui-seed/          script nạp 10 phim mới & suất chiếu qua HTTP API
tests/integration bộ kiểm thử tích hợp (Python, không cần cài thêm)
docs/             ERD, Use Case, DFD, báo cáo của từng thành viên
scripts/          init-db, start-all, stop-all, setup-git
```

## Nạp thêm dữ liệu & tài nguyên (UI Seed)
Để làm phong phú danh mục phim cho giao diện người dùng (từ 5 phim gốc lên 15 phim đa dạng thể loại cùng suất chiếu 7 ngày tới):
```bash
# Đảm bảo Movie Service (cổng 5001) và Showtime Service (cổng 5002) đang chạy
python ui-seed/seed-movies.py
```
*Script có tính lũy thừa (idempotent), chạy lặp lại an toàn không sinh phim hay suất chiếu trùng lặp.*

## Nguồn poster & trailer
Toàn bộ dữ liệu hình ảnh và video trailer đều được xác thực từ các nguồn công khai chính thức:
- **Poster phim**: Khai thác từ [The Movie Database (TMDB)](https://www.themoviedb.org/) và [Wikimedia Commons](https://commons.wikimedia.org/). Ảnh được tải về cục bộ tại `client/assets/posters/` (tỉ lệ 2:3) và `client/assets/backdrops/` (hero banner) để hệ thống hoạt động hoàn toàn offline.
- **Trailer YouTube**: Sử dụng mã nhúng video chính thức từ các kênh phân phối của hãng phim (Marvel Entertainment, Warner Bros. Pictures, Universal Pictures, Pixar, Sony Pictures, Illumination, Ly Hai Production, Trấn Thành Town, Galaxy Cinema, CJ ENM Vietnam, NEON, Well Go USA). Đã xác thực thành công qua YouTube oEmbed API.
- **Metadata mở rộng**: Quản lý độc lập tại `client/js/movie-extras.js` (không can thiệp CSDL backend của Movie Service), cung cấp nhãn tuổi (P, T13, T16, T18), thể loại chi tiết, tóm tắt tiếng Việt và liên kết trailer.

## Tạo repository GitHub
Tạo repo **rỗng**, rồi nhóm trưởng chạy một lần: `bash scripts/setup-git.sh https://github.com/<tài-khoản>/soa-datve.git`
(tạo `main`, `develop` và 6 nhánh `feature/tvN-*`). Sau đó bật bảo vệ nhánh `main`/`develop` (bắt buộc Pull Request).

