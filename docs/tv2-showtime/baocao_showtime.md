# BÁO CÁO THIẾT KẾ VÀ TRIỂN KHAI DỊCH VỤ SHOWTIME (SHOWTIME SERVICE)

**Dự án:** Hệ thống Đặt vé xem phim Microservices (SOA)  
**Thành viên phụ trách:** TV2 - Showtime Service  
**Cổng dịch vụ (Port):** `5002`  
**Công nghệ:** PHP 8.1+ (Pure PHP), MySQL (`showtime_db`)

---

## 1. Giới thiệu dịch vụ (Service Overview)

Showtime Service đảm nhận vai trò quản lý lịch chiếu và giá vé cho toàn hệ thống đặt vé xem phim:
- **Client App (`:8080`)**: Truy vấn danh sách lịch chiếu theo từng bộ phim (`movie_id`).
- **Admin Dashboard (`:8081`)**: Quản lý CRUD (Thêm, Sửa, Xóa) các suất chiếu và điều chỉnh giá vé.
- **Booking Service (`:5004`)**: Truy vấn thông tin chi tiết suất chiếu và giá vé để tính toán tổng tiền đơn hàng.

---

## 2. Thiết kế Cơ sở dữ liệu (Database Design)

- **Tên CSDL:** `showtime_db`
- **Bảng chính:** `showtimes`
- **Nguyên tắc SOA:** Áp dụng mô hình *Database-per-service*. Không sử dụng Foreign Key vật lý liên kết sang CSDL khác.

### Cấu trúc bảng `showtimes`:
| Trường | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| `id` | `INT` (PK, AUTO_INCREMENT) | Mã suất chiếu |
| `movie_id` | `INT` (NOT NULL) | Mã phim (Khóa ngoại logic kết nối tới `movie_db.movies`) |
| `cinema` | `VARCHAR(150)` | Tên rạp chiếu (VD: CGV Vincom Đồng Khởi) |
| `room` | `VARCHAR(50)` | Phòng chiếu (VD: P1, P2) |
| `time` | `DATETIME` | Thời gian chiếu phim |
| `price` | `INT` | Giá vé (VND) |
| `created_at` | `TIMESTAMP` | Thời gian tạo bản ghi |

---

## 3. Danh sách API Endpoints

Service chạy độc lập tại địa chỉ: `http://localhost:5002`

| HTTP Method | Endpoint | Mô tả | Query / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/showtimes` | Lấy danh sách suất chiếu | Optional: `?movie_id={id}` |
| `GET` | `/api/showtimes/{id}` | Lấy chi tiết 1 suất chiếu | N/A |
| `POST` | `/api/showtimes` | Thêm suất chiếu mới | JSON `{movie_id, cinema, room, time, price}` |
| `PUT` | `/api/showtimes/{id}` | Cập nhật suất chiếu | JSON `{movie_id, cinema, room, time, price}` |
| `DELETE` | `/api/showtimes/{id}` | Xóa suất chiếu | N/A |

---

## 4. Hướng dẫn khởi chạy (Execution Guide)

1. **Khởi tạo CSDL MySQL:**
   Chạy file SQL tạo CSDL `showtime_db` và nạp dữ liệu mẫu.

2. **Chạy dịch vụ PHP:**
   Mở Terminal tại thư mục mã nguồn `tv2-showtime` và thực thi:
   ```bash
   php -S 0.0.0.0:5002 router.php

---

> **Ghi chú Baseline V2 (nhóm trưởng thêm khi gộp repository):** nội dung phía trên là báo cáo giữa kỳ của TV2, giữ nguyên.
> Từ Baseline V2, API dùng **camelCase**: tham số lọc là `?movieId=` và trường JSON là `movieId` (tên cũ `movie_id` vẫn được nhận để tương thích, nhưng response luôn trả `movieId`).
> Lỗi trả về có thêm trường `code`. Chi tiết hợp đồng: `API_CONTRACT.md` mục 3.
