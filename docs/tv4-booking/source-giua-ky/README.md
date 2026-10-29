# Booking Service – TV4 (C#)

| Mục | Nội dung |
|-----|----------|
| Người làm | Trần Trung Hiếu – 52400047 |
| Branch | `tv4-booking` |
| Cổng | **5004** |
| CSDL | MySQL `booking_db` (mặc định) hoặc SQL Server (`DB_PROVIDER=sqlserver`) |
| Giữa kỳ (core) | `HttpListener` + ADO.NET (MySqlConnector / Microsoft.Data.SqlClient) + `System.Text.Json` |
| Cuối kỳ (framework) | ASP.NET Core 8 Minimal API + EF Core + JWT middleware + HttpClientFactory |
| Dữ liệu mẫu | `db/seed.sql` (khớp `seed/booking_db.sql`, Phụ lục A.4) |
| Trang admin | `admin/pages/admin_booking.html` (chỉ xem, nhãn màu trạng thái) |

## Cấu trúc

```
booking-service/
├── .env.example            # sao chép thành .env (không commit .env)
├── docker-compose.yml      # MySQL 8 riêng cho Booking, cổng 3307
├── demo_api.ps1            # chạy lần lượt các lệnh demo bằng curl.exe (PowerShell)
├── BookingService.sln
├── db/
│   ├── schema.sql, seed.sql          # MySQL (chạy lặp lại được)
│   └── sqlserver/schema.sql, seed.sql
└── src/
    ├── BookingService/               # mã nguồn API
    │   ├── Program.cs                # điểm vào
    │   ├── Config/AppConfig.cs       # đọc .env / biến môi trường
    │   ├── Http/                     # HttpListener, định tuyến, CORS, JSON
    │   ├── Domain/                   # kiểm tra body (1.0), quy tắc ghế (2.2)
    │   ├── Services/BookingManager.cs# tạo đơn PENDING (2.1–2.4)
    │   └── Data/                     # ADO.NET, transaction + khóa suất chiếu
    └── BookingService.Tests/         # 12 test đơn vị + 17 test API thật
```

## Cách chạy

**1. CSDL** – chọn một cách:

- Docker (khuyên dùng): `copy .env.example .env`, điền `DB_PASSWORD`, rồi `docker compose up -d`.
  Lần đầu container tự chạy `schema.sql` và `seed.sql`. MySQL ở cổng **3307** để không trùng MySQL của service khác.
- MySQL có sẵn (XAMPP, MySQL Installer): đổi `DB_PORT=3306` trong `.env`, rồi chạy
  `mysql -u root -p -e "source db/schema.sql"` và `mysql -u root -p -e "source db/seed.sql"`.
  (PowerShell không hỗ trợ `mysql ... < file.sql`, nên dùng `source`.)
- SQL Server: `DB_PROVIDER=sqlserver`, `DB_HOST=localhost\SQLEXPRESS` (để trống `DB_USER` nếu đăng nhập bằng tài khoản Windows), chạy 2 file trong `db/sqlserver/` bằng SSMS.

**2. Service**

```bash
cd booking-service/src/BookingService
dotnet run
# hoặc từ thư mục booking-service: dotnet run --project src/BookingService
```

Service đọc `.env` ở thư mục hiện tại hoặc thư mục cha, kiểm tra kết nối CSDL khi khởi động (thử 5 lần) rồi lắng nghe `http://localhost:5004/`.

**3. Kiểm thử** (service phải đang chạy)

```bash
cd booking-service
dotnet run --project src/BookingService.Tests            # 29 PASS trên CSDL mới
powershell -ExecutionPolicy Bypass -File .\demo_api.ps1  # các lệnh curl.exe để chụp ảnh
```

**4. Trang admin**

```bash
cd soa-datve
python -m http.server 8081 --bind 127.0.0.1 --directory admin/pages
# mở http://localhost:8081/admin_booking.html
```

## API (giữa kỳ)

| Method & URL | Input | Thành công | Lỗi |
|---|---|---|---|
| `POST /api/booking` | `{movieId, showtimeId, seats[], pricePerSeat, username}` | 201 + đơn `{id, totalPrice, status:"PENDING", ...}` + header `Location` | 400 dữ liệu sai / JSON sai / ghế trùng, 413 body > 16 KiB, 503 suất bận, 500 |
| `GET /api/booking` | – | 200 + mảng đơn (mới nhất trước) | 500 |
| `GET /api/booking/{id}` | id nguyên dương | 200 + một đơn | 400, 404, 500 |
| `OPTIONS` hai đường dẫn trên | – | 204 + CORS | – |
| Method khác | – | – | 405 + header `Allow` |

Quy ước: JSON `{"status":"success","data":…}` hoặc `{"status":"error","message":"…"}`; mọi câu SQL có tham số.

Quy tắc ghế: ghế dạng `A1`–`Z99`, 1–10 ghế mỗi đơn, không lặp. Ghế bị coi là đã đặt nếu thuộc đơn **cùng suất chiếu** có trạng thái khác `CANCELLED`. Bước kiểm tra và ghi đơn chạy trong transaction có khóa theo suất chiếu, nên nhiều request đặt cùng một ghế cùng lúc thì chỉ một request thành công.

Lưu ý: lệnh mẫu trong phiếu (đặt `A1, A2` suất 1) trả **400**, vì 2 ghế này đã thuộc đơn #1 (PAID) trong dữ liệu mẫu. Đây là kết quả đúng.

## Lỗi thường gặp

- **`Không mở được cổng 5004`**: cổng đang bị chương trình khác dùng, hoặc dùng prefix `http://+:5004/` mà chưa đăng ký. Muốn máy khác trong nhóm gọi được: chạy CMD với quyền Admin `netsh http add urlacl url=http://+:5004/ user=Everyone`, rồi đặt `LISTEN_PREFIXES=http://+:5004/`.
- **Gọi bằng `http://127.0.0.1:5004` bị 400 trên Windows**: với prefix mặc định, HttpListener chỉ nhận host `localhost`. Hãy dùng `http://localhost:5004`.
- **PowerShell**: dùng `curl.exe`, không dùng `curl` (alias của Invoke-WebRequest).
- **Reset dữ liệu demo**: `mysql -u root -p -e "DROP DATABASE IF EXISTS booking_db"`, rồi chạy lại `schema.sql` và `seed.sql` (chỉ làm trên máy mình).

## Việc cần làm

- [x] P1 CSDL + seed khớp `seed/` (`db/`)
- [x] P2 ERD (`docs/tv4-booking/ERD_booking.png` + `.drawio`)
- [x] P3 Use Case (`UC_booking`)
- [x] P4 DFD mức 0, 1 (`DFD0_booking`, `DFD1_booking`)
- [x] P5 DFD mức 2 (`DFD2_booking`, phân rã 2.0)
- [x] P6 API code thuần chạy được + bộ test
- [x] P7 Trang admin (`admin/pages/admin_booking.html`)
- [x] P8 Báo cáo chức năng (`docs/tv4-booking/05_baocao_booking.docx`)
- [x] Việc chung TV4: `docs/tong-the/UC_TongThe.png`, `DFD1_TongThe.png` (+ `.drawio`)
