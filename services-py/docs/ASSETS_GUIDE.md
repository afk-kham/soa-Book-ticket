# ASSETS_GUIDE — File nặng, frontend, tài liệu: giữ nguyên & cách tự bổ sung

**Quy tắc cho giai đoạn dựng khung:** không tạo, sao chép, di chuyển, đổi tên, chuyển đổi hay nhúng file nhị phân (ảnh, DOCX, PDF, PPTX, draw.io, video, dữ liệu lớn). Gói khung này **không chứa file nhị phân nào** và **không sửa** bất kỳ file HTML/CSS/JS nào. Việc thêm/di chuyển file nặng do **người dùng tự làm bằng tay**.

Danh sách dưới đây lấy từ `git ls-files` trên `main` @ `326602e` (không mở nội dung file nặng).

## 1. Frontend & tài nguyên cần bảo toàn (KHÔNG SỬA)

| Loại | Vị trí hiện có (giữ nguyên) | Số lượng / ví dụ | Ghi chú bảo toàn liên kết |
|---|---|---|---|
| Admin HTML/CSS/JS | `admin/index.html`, `admin/pages/{booking,movie,notification,payment,showtime,user}.html`, `admin/css/admin.css`, `admin/js/{common,config,movie-extras}.js` | 11 file text | `admin/js/config.js` là **nơi duy nhất** khai báo địa chỉ service (`http://<host>:5001…5006`). Giữ nguyên cổng thì Admin chạy được với service Python |
| Admin ảnh | `admin/assets/posters/*.jpg` (15), `admin/assets/backdrops/*.jpg` (6) | JPG | Đường dẫn tương đối do `movie-extras.js`/trang tham chiếu — không đổi tên |
| Client HTML/CSS/JS | `client/index.html`, `client/css/client.css`, `client/js/{app,barcode,config,movie-extras,qr}.js` | 7 file text | `client/js/config.js` khai báo `window.API`, `POSTER_DIR = "img/posters/"` |
| Client ảnh | `client/assets/posters/*.jpg` (15), `client/assets/backdrops/*.jpg` (6), `client/img/posters/poster1..5.svg` | JPG, SVG | Giữ nguyên đường dẫn |
| Figma plugin | `design/figma-plugin/{code.js,manifest.json,README.md}` | 3 file | Không liên quan backend |
| Ảnh chụp màn hình ở gốc repo | `admin_{booking,movie,overview,showtime}_1440.png`, `client_{book,home,my,pay,ticket}_*.png`, `client_sandbox_390.png`, `test_before_client_1440.png` | 16 PNG | Không file text nào tham chiếu (đã `git grep`); **không di chuyển tự động** (D-17) |
| Sơ đồ / báo cáo | xem §2 | `.drawio`, `.png`, `.mmd`, `.docx`, `.pdf` | Không đổi tên/di chuyển |
| Script & seed phía giao diện | `scripts/*`, `tests/integration/*`, `ui-seed/seed-movies.py` | | Không sửa ở giai đoạn này |

## 2. Tài liệu & sơ đồ hiện có theo thành viên (GIỮ NGUYÊN)

| Thư mục | Nội dung hiện có |
|---|---|
| `docs/tv1-movie/` | `05_baocao_movie.docx`, `baocao_movie.md`, `DFD0/1/2_movie` (`.drawio` + `.png`; DFD2 là `DFD2_movie.drawio.png`), `ERD_movie`, `UC_movie` |
| `docs/tv2-showtime/` | `baocao_showtime.md`, `README.md`, `DFD0/1/2_showtime`, `ERD_showtime`, `UC_showtime` (`.drawio` + `.png`) |
| `docs/tv3-user/` | `05_baocao_user.docx`, `DFD0/1_user`, `ERD_user`, `UC_user` (`.drawio` + `.png`); **`DFD2_user` chỉ có `.drawio`, chưa có `.png`** |
| `docs/tv4-booking/` | `05_baocao_booking.docx`, `reports/05_baocao_booking.pdf`, `DFD0/1/2_booking`, `ERD_booking`, `UC_booking`, `anh-ket-qua/*.png` (9), `admin_booking_giua_ky.html`, `source-giua-ky/` (C#, docker-compose, SQL) |
| `docs/tv5-payment/` | `BAO_CAO_TV5.pdf`, `PDR_TV5_Payment_Service_Nodejs.pdf`, `dfd-level-1/2`, `erd`, `use-case` (`.mmd` + `.png`), `pasted_file_G4JHt3_image.png` |
| `docs/tv6-notification/` | `05_baocao_notification.pdf`, `DFD0/1/2_notification`, `ERD_notification`, `UC_notification` (`.drawio` + `.png`) |
| `docs/tong-the/` | `ERD.jpg`, `ERD_TongThe.drawio`, `UC_TongThe`, `DFD1_TongThe`, `dfd0`, `dfd2`, `erd` (`.drawio` + `.png`), `README.md` |
| `docs/tai-lieu/` | `Ke_Hoach_Trien_Khai_SOA_Dat_Ve_Phim_v2_1.docx`, `Phieu_Giao_Viec_Chuan_Bi_Giua_Ky.docx` |

> Sau migration, ERD/DFD của từng service sẽ lệch (MySQL/Mongo → SQLite, ngôn ngữ). Việc cập nhật sơ đồ do từng thành viên **tự làm bằng công cụ vẽ của họ** (draw.io…) — khung không tạo sơ đồ thay.

## 3. Nơi đặt file nặng mới (đề xuất; thư mục chưa tạo nếu chưa có)

| Loại file | Vị trí đích đề xuất | Hiện có? | Ai thêm | Cách thêm (thủ công) |
|---|---|---|---|---|
| Sơ đồ ERD/DFD/UC sau migration (`.drawio`, `.png`) | `docs/tv<N>-<service>/` (thư mục đã có) | Có | TV tương ứng | Lưu file mới **tên mới** (ví dụ thêm hậu tố `_sqlite`) cạnh file cũ; không ghi đè file cũ |
| Báo cáo (`.docx`, `.pdf`) | `docs/tv<N>-<service>/` | Có | TV tương ứng | Như trên |
| Ảnh kết quả chạy / chụp màn hình mới | `docs/tv<N>-<service>/anh-ket-qua/` (TV4 đã có; các TV khác tự tạo nếu cần) | Một phần | TV tương ứng | Chép tay vào thư mục |
| Ảnh chụp màn hình hiện nằm ở gốc repo | `docs/screenshots/` (**chưa tồn tại**) | Không | Nhóm trưởng, PR riêng | `mkdir docs/screenshots && git mv *.png docs/screenshots/` — **chỉ khi** nhóm đồng ý (D-17); khung không làm |
| Poster/backdrop phim | `admin/assets/…`, `client/assets/…`, `client/img/posters/` | Có | Nhóm trưởng | Thêm file mới tên mới; trường `poster` của phim trỏ tới tên file |
| Sao lưu SQLite | **Ngoài repo** (ví dụ `~/backups/soa/`) | — | Người vận hành | `sqlite3 <db> ".backup '<đích>'"`; `*.db` đã bị `.gitignore` |
| Dữ liệu lớn, video, file build | **Không đưa vào repo** | — | — | Dùng Git LFS hoặc lưu ngoài nếu thật sự cần (hỏi nhóm trưởng) |

## 4. Kiểm tra bảo toàn sau khi áp dụng khung

Xem `HUONG_DAN_AP_DUNG.md` §2: `git status` chỉ được liệt kê file **mới** (`??`) dưới `services-py/`; không dòng `M` (sửa), `D` (xóa), `R` (đổi tên) nào.
