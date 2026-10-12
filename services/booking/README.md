# Booking Service (TV4) — C# · cổng 5004 · `booking_db`

**Service điều phối** luồng đặt vé: User → Movie → Showtime → lưu PENDING → Payment → PAID/CANCELLED → Notification.
.NET 8, `HttpListener`, ADO.NET (MySqlConnector). Không dùng ASP.NET.

```bash
cd services/booking
cp .env.example .env              # sửa DB_USER / DB_PASSWORD và địa chỉ các service
dotnet run                        # http://localhost:5004
```
- Windows mặc định nghe `http://localhost:5004/` (không cần Administrator). Muốn máy khác gọi được: `BOOKING_PREFIX=http://+:5004/` và chạy bằng quyền Administrator.
- Booking **không bao giờ đọc DB của service khác**; chỉ gọi API (`Upstream.cs`).
- `BOOKING_STORE=memory` chỉ dùng để thử nhanh không cần MySQL.

| Tệp | Vai trò |
|---|---|
| `Program.cs` | Định tuyến, luồng đặt vé, xử lý lỗi |
| `Upstream.cs` | Gọi service khác (JSON, timeout, 503 khi sập) |
| `BookingStore.cs` | Truy cập `booking_db` (+ kho bộ nhớ để test) |
| `Config.cs`, `Models.cs` | Cấu hình, mô hình, JSON camelCase |

Luồng và bảng xử lý lỗi: `INTEGRATION_FLOW.md`. API: `API_CONTRACT.md` mục 5.
