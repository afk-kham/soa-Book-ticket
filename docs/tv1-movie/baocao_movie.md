# BÁO CÁO CHỨC NĂNG DỊCH VỤ QUẢN LÝ PHIM (MOVIE SERVICE)
**HỌC PHẦN: KIẾN TRÚC HƯỚNG DỊCH VỤ (SOA)**  
**BÀI TẬP LỚN: HỆ THỐNG ĐẶT VÉ XEM PHIM THEO KIẾN TRÚC MICROSERVICES**

---

### THÔNG TIN SINH VIÊN & SERVICE
- **Họ và tên sinh viên:** Lý Khôi Nguyên
- **Mã số sinh viên (MSSV):** 52400025
- **Vai trò trong nhóm:** Thành viên 1 (TV1)
- **Tên dịch vụ:** Movie Service (Dịch vụ Quản lý Phim)
- **Cổng hoạt động:** `5001` (Lắng nghe: `0.0.0.0:5001`)
- **Ngôn ngữ & Công nghệ giữa kỳ:** Python 3.10+ (Code thuần với `http.server`, `ThreadingHTTPServer`, `pymysql`)
- **Cơ sở dữ liệu:** MySQL `movie_db` (Bảng `movies`)
- **Ngày nộp:** 04/10/2026

---

## 1. GIỚI THIỆU DỊCH VỤ (ROLE & BOUNDARY)
Trong hệ thống kiến trúc hướng dịch vụ (Microservices) cho bài toán Đặt vé xem phim, **Movie Service** đóng vai trò là dịch vụ danh mục trung tâm (Catalog Service), chịu trách nhiệm quản lý toàn bộ vòng đời của dữ liệu phim (tên phim, thể loại, thời lượng, poster).

- **Vị trí & tương tác trong hệ thống:**
  - **Khách hàng (Client App - Cổng 8080):** Gọi trực tiếp vào Movie Service để lấy danh sách phim đang chiếu và xem chi tiết phim (công khai).
  - **Trang quản trị (Admin Dashboard - Cổng 8081):** Gọi vào Movie Service để thực hiện các nghiệp vụ quản lý: Thêm, Sửa, Xóa và Cập nhật danh mục phim.
  - **Showtime Service (Cổng 5002) & Booking Service (Cổng 5004):** Dựa vào mã định danh logic `movie_id` từ Movie Service để tạo suất chiếu và đơn đặt vé.
  - **Độc lập dữ liệu:** Movie Service sở hữu độc quyền CSDL `movie_db`. Các service khác không được can thiệp trực tiếp vào bảng `movies` mà chỉ giao tiếp thông qua giao diện chuẩn REST API.

---

## 2. CÔNG NGHỆ ÁP DỤNG & CÁCH TRIỂN KHAI
### 2.1. Lựa chọn công nghệ
- **Ngôn ngữ:** Python 3.10+.
- **Bộ máy Web giữa kỳ:** Thư viện chuẩn `http.server` với hai lớp chính:
  - `BaseHTTPRequestHandler`: Xử lý bóc tách HTTP Request (Method, Header, Body, Path).
  - `ThreadingHTTPServer`: Hỗ trợ đa luồng (Multi-threading), cho phép xử lý đồng thời nhiều kết nối từ Client và Admin Dashboard mà không gây nghẽn (blocking).
  - *Lý do chọn:* Đáp ứng chính xác yêu cầu của giảng viên về việc hiểu sâu bản chất tầng mạng/giao thức HTTP core bằng tay trước khi sử dụng framework ở cuối kỳ.
- **Bộ định tuyến (Router):** Tự xây dựng cơ chế ánh xạ URL động bằng biểu thức chính quy (`re.compile(r"^/api/movies/(\d+)$")`).
- **Driver CSDL:** `pymysql` kết hợp `DictCursor`, giúp trả dữ liệu theo dạng Dictionary tương thích với JSON.
- **Bảo mật SQL:** Áp dụng hoàn toàn cơ chế Parameterized Query (`%s`) ngăn ngừa triệt để lỗi SQL Injection.
- **Hỗ trợ CORS & Preflight:** Tích hợp đầy đủ các Header `Access-Control-Allow-*` và xử lý phương thức `OPTIONS` trả mã `204 No Content`.

### 2.2. Hướng dẫn chạy nhanh
```bash
# 1. Cài đặt phụ thuộc
pip install -r requirements.txt

# 2. Khởi tạo CSDL MySQL
mysql -u root -p < 01_db/schema.sql
mysql -u root -p < 01_db/seed.sql

# 3. Khởi động Server
python movie_service.py
```

---

## 3. THIẾT KẾ CƠ SỞ DỮ LIỆU (DATABASE & ERD)

### 3.1. Sơ đồ thực thể liên kết (ERD)
*(Chèn hình ảnh `ERD_movie.png` được xuất từ `02_sodo/ERD_movie.drawio` vào đây)*

### 3.2. Cấu trúc bảng `movies` (movie_db)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả ý nghĩa |
|---|---|---|---|
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | Mã định danh duy nhất của bộ phim |
| `title` | VARCHAR(255) | NOT NULL | Tên tác phẩm điện ảnh |
| `genre` | VARCHAR(100) | NULL | Thể loại phim (Hành động, Tâm lý, v.v.) |
| `duration` | INT | NULL | Thời lượng phát sóng (tính theo phút) |
| `poster` | VARCHAR(255) | NULL | Tên tệp hoặc URL hình ảnh áp phích |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Thời điểm tạo bản ghi |

### 3.3. Giải thích khóa ngoại logic (Logical Foreign Key)
Theo triết lý Database-per-service của kiến trúc Microservices:
- Bảng `movies` không chứa bất kỳ khóa ngoại vật lý (`FOREIGN KEY`) nào liên kết sang service khác.
- Tuy nhiên, trường `id` của bảng này sẽ đóng vai trò là **khóa ngoại logic** cho:
  - Bảng `showtimes.movie_id` của **Showtime Service** (để biết suất chiếu thuộc phim nào).
  - Bảng `bookings.movie_id` của **Booking Service** (để lưu thông tin phim trong vé đặt).
- Tính toàn vẹn dữ liệu được đảm bảo thông qua logic của tầng ứng dụng và hợp đồng API chung, không dựa vào ràng buộc cứng của hệ quản trị cơ sở dữ liệu.

---

## 4. PHÂN TÍCH THIẾT KẾ HỆ THỐNG (USE CASE & DFD)

### 4.1. Sơ đồ Use Case mức ý niệm
*(Chèn hình ảnh `UC_movie.png` được xuất từ `02_sodo/UC_movie.drawio` vào đây)*

**Bảng đặc tả Use Case chính:**
| Tên Use Case | Tác nhân (Actor) | Luồng nghiệp vụ chính | Ngoại lệ |
|---|---|---|---|
| **Xem danh sách phim** | Khách, Admin, Service khác | Gửi yêu cầu -> Nhận toàn bộ danh sách phim (mã, tên, thể loại, thời lượng, poster). | CSDL mất kết nối -> Trả mã lỗi 500. |
| **Xem chi tiết phim** | Khách, Admin, Service khác | Truyền `id` phim -> Nhận chi tiết phim tương ứng. | Không tìm thấy `id` -> Trả mã lỗi 404. |
| **Thêm phim mới** | Quản trị viên | Nhập tên phim, thời lượng, thể loại -> Lưu phim mới -> Nhận bản ghi vừa tạo. | Thiếu `title` hoặc `duration <= 0` -> Trả lỗi 400. |
| **Sửa thông tin phim** | Quản trị viên | Chọn `id` phim và nhập các thông tin cần sửa -> Cập nhật CSDL. | `id` không tồn tại -> Trả mã 404; dữ liệu sai -> Trả lỗi 400. |
| **Xóa phim** | Quản trị viên | Chọn `id` phim và xác nhận xóa -> Xóa khỏi bảng `movies`. | `id` không tồn tại -> Trả mã 404. |

### 4.2. Sơ đồ luồng dữ liệu (DFD - Chuẩn Gane-Sarson)

#### A. DFD Mức 0 (Sơ đồ ngữ cảnh)
*(Chèn ảnh `DFD0_movie.png` vào đây)*
- **Mô tả:** Hệ thống Movie Service đóng vai trò là một tiến trình trung tâm (`0.0`). Tác nhân Khách gửi yêu cầu tra cứu và nhận dữ liệu phim; Tác nhân Quản trị viên gửi các thao tác quản trị (CRUD) và nhận kết quả phản hồi trạng thái.

#### B. DFD Mức 1 (Phân rã chức năng)
*(Chèn ảnh `DFD1_movie.png` vào đây)*
- **Mô tả:** Tách service thành 2 tiến trình cốt lõi:
  - `1.0 Tra cứu phim`: Đọc dữ liệu từ kho `D1 | movies` để cung cấp cho Khách.
  - `2.0 Quản lý phim`: Tiếp nhận thao tác từ Quản trị viên để ghi/cập nhật/xóa bản ghi trong kho `D1 | movies`.

#### C. DFD Mức 2 (Phân rã tiến trình 2.0 Quản lý phim)
*(Chèn ảnh `DFD2_movie.png` vào đây)*
- **Mô tả:** Tiến trình 2.0 được chi tiết hóa thành 3 bước logic cân bằng luồng vào ra:
  - `2.1 Tiếp nhận & Kiểm tra dữ liệu đầu vào`: Xác thực trường `title` và `duration`. Nếu không hợp lệ chuyển sang 2.3 trả lỗi HTTP 400.
  - `2.2 Thao tác CSDL`: Thực thi truy vấn SQL có tham số tới kho `D1 | movies`.
  - `2.3 Tạo phản hồi JSON`: Chuẩn hóa dữ liệu trả về theo format chung `{ status, data/message }`.

---

## 5. ĐẶC TẢ & KẾT QUẢ KIỂM THỬ API (P6)

### 5.1. Bảng hợp đồng API
| Phương thức | Đường dẫn (URL) | Input (Body / Param) | Output thành công | Mã HTTP |
|---|---|---|---|---|
| `GET` | `/api/movies` | Không | `{"status":"success", "data":[...]}` | `200 OK` |
| `GET` | `/api/movies/{id}` | `id` trên URL | `{"status":"success", "data":{...}}` | `200 OK` / `404 Not Found` |
| `POST` | `/api/movies` | JSON `{title, genre, duration, poster}` | `{"status":"success", "data":{...}}` | `201 Created` / `400 Bad Request` |
| `PUT` | `/api/movies/{id}` | `id` trên URL, JSON cập nhật | `{"status":"success", "data":{...}}` | `200 OK` / `404 Not Found` |
| `DELETE` | `/api/movies/{id}` | `id` trên URL | `{"status":"success", "data":{"id":..., "deleted":true}}` | `200 OK` / `404 Not Found` |

### 5.2. Ảnh chụp kết quả kiểm thử API thực tế
*(Chụp màn hình cửa sổ terminal khi chạy các lệnh curl hoặc Postman và dán vào các mục dưới đây)*

1. **Kiểm thử lấy danh sách phim (GET /api/movies):**  
   *(Dán ảnh chụp curl/Postman)*
2. **Kiểm thử lấy chi tiết phim (GET /api/movies/1):**  
   *(Dán ảnh chụp curl/Postman)*
3. **Kiểm thử thêm phim mới (POST /api/movies):**  
   *(Dán ảnh chụp curl/Postman)*
4. **Kiểm thử sửa thông tin phim (PUT /api/movies/1):**  
   *(Dán ảnh chụp curl/Postman)*
5. **Kiểm thử xóa phim (DELETE /api/movies/6):**  
   *(Dán ảnh chụp curl/Postman)*
6. **Kiểm thử trường hợp lỗi (Validation / 404):**  
   *(Dán ảnh chụp curl/Postman trả về HTTP 400 hoặc 404)*

---

## 6. GIAO DIỆN QUẢN TRỊ ADMIN (P7)
- **Tập tin giao diện:** `admin_movie.html` (chạy độc lập hoặc qua cổng `8081`).
- **Tính năng hoàn thành:**
  - Hiển thị danh sách toàn bộ các bộ phim dưới dạng bảng trực quan (có gắn nhãn thể loại, mã định danh, thời lượng, poster).
  - Nút "Tải lại" dữ liệu tức thời.
  - Hộp thoại modal "Thêm phim mới" và "Chỉnh sửa thông tin phim".
  - Nút "Xóa phim" có hộp thoại xác nhận cảnh báo trước khi thực thi lệnh gọi API.
  - Tự động bắt lỗi mất kết nối (khi server tắt) và hiển thị thông báo chỉ dẫn trực quan cho quản trị viên thay vì để màn hình trắng.

*(Dán ảnh chụp giao diện `admin_movie.html` hiển thị dữ liệu thật và ảnh khi thao tác Thêm/Sửa/Xóa vào đây)*

---

## 7. KẾT LUẬN & HƯỚNG PHÁT TRIỂN
### 7.1. Kết quả đạt được
- Hoàn thành đầy đủ 8 sản phẩm thành phần theo yêu cầu của Phiếu giao việc giữa kỳ môn SOA.
- Xây dựng thành công máy chủ API mỏng bằng thư viện lõi `http.server` của Python, giải quyết tốt bài toán bất đồng bộ/đa luồng bằng `ThreadingHTTPServer`.
- Định tuyến Regex chính xác và tuân thủ 100% hợp đồng API chung của nhóm, sẵn sàng ghép nối với các service còn lại.

### 7.2. Khó khăn gặp phải & giải pháp
- **Khó khăn:** Không được sử dụng framework web (như FastAPI hay Flask) dẫn đến việc phải tự phân tích URL động, tự bóc tách body JSON, tự cấu hình CORS và xử lý thủ công các phương thức HTTP.
- **Giải pháp:** Xây dựng các hàm dùng chung `_send_json`, `_read_json_body`, biên dịch sẵn các biểu thức Regex và tận dụng `ThreadingHTTPServer` để tối ưu hóa hiệu năng.

### 7.3. Kế hoạch chuyển đổi sang Framework ở cuối kỳ
- Chuyển đổi mã nguồn từ `http.server` sang framework **Django** theo đúng chỉ định của giảng viên.
- Sử dụng **Django ORM** để quản lý model `Movie` thay cho truy vấn thô.
- Cấu hình thư viện `django-cors-headers` và tích hợp kiểm tra chữ ký xác thực **JWT (JSON Web Token)** với quyền `ADMIN` cho các thao tác ghi (POST/PUT/DELETE).
- Tận dụng trang quản trị mặc định `Django Admin` làm điểm cộng cho đồ án cuối kỳ.
