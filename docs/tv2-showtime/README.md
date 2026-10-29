# Tài liệu TV2 — Showtime
Đặt tại đây: ERD, Use Case, DFD 0/1/2, báo cáo `.docx`/`.pdf` của TV2.
Mô tả API: `API_CONTRACT.md` mục 3. (Bản Postman cũ dùng `/showtime_service.php` đã lỗi thời — xuất lại từ API mới.)

## Sản phẩm của TV2 (đã gộp vào Baseline V2)
| Sản phẩm | Tệp |
|---|---|
| P2 ERD | `ERD_showtime.png`, `ERD_showtime.drawio` |
| P3 Use Case | `UC_showtime.png`, `UC_showtime.drawio` |
| P4 DFD mức 0, 1 | `DFD0_showtime.png`, `DFD1_showtime.png` (+ `.drawio`) |
| P5 DFD mức 2 | `DFD2_showtime.png`, `DFD2_showtime.drawio` |
| P8 Báo cáo chức năng | `baocao_showtime.md` |

Ký hiệu DFD: Gane–Sarson. ERD: chân chim; khóa ngoại sang service khác vẽ nét đứt.
Mã nguồn tương ứng: `services/showtime/` (đã dùng `showtime_db`, CRUD đầy đủ, camelCase).
