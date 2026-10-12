# TEAM_RULES — Quy tắc làm việc của nhóm

## 1. Ai sở hữu gì
| Thành viên | Service | Thư mục được sửa | Nhánh |
|---|---|---|---|
| TV1 | Movie | `services/movie/`, `database/movie/`, `docs/tv1-movie/` | `feature/tv1-movie` |
| TV2 | Showtime | `services/showtime/`, `database/showtime/`, `docs/tv2-showtime/` | `feature/tv2-showtime` |
| TV3 | User | `services/user/`, `database/user/`, `docs/tv3-user/` | `feature/tv3-user` |
| TV4 | Booking | `services/booking/`, `database/booking/`, `docs/tv4-booking/` | `feature/tv4-booking` |
| TV5 | Payment | `services/payment/`, `database/payment/`, `docs/tv5-payment/` | `feature/tv5-payment` |
| TV6 | Notification | `services/notification/`, `database/notification/`, `docs/tv6-notification/` | `feature/tv6-notification` |
| Nhóm trưởng | Chung | `README.md`, `*_CONTRACT.md`, `ARCHITECTURE.md`, `INTEGRATION_*`, `admin/`, `client/`, `tests/`, `scripts/` | `develop` |

**Chỉ sửa thư mục của mình.** Cần đổi thứ thuộc người khác → mở Issue hoặc nhắn người đó.

## 2. Các thứ KHÔNG ĐƯỢC tự ý đổi
- Cổng, tên CSDL, tên bảng/cột, **id và giá trị seed** có sẵn.
- Định dạng response (envelope), tên trường JSON, mã lỗi → chỉ đổi bằng PR sửa `API_CONTRACT.md`.
- `admin/css/admin.css`, `admin/js/common.js`, `admin/js/config.js` → không tạo CSS/khung riêng cho trang của mình. Cần tính năng mới trong khung → báo nhóm trưởng.
- Không commit `.env`, mật khẩu, thư mục `bin/ obj/ node_modules/ target/ __pycache__/`.

## 3. Quy trình Git
```
main      ← chỉ nhận từ develop khi cả nhóm đã qua INTEGRATION_CHECKLIST
develop   ← nhánh tích hợp
feature/tvN-<service> ← mỗi người làm ở đây
```
1. `git checkout develop && git pull` → `git checkout feature/tvN-...`
2. Commit nhỏ, thông điệp rõ: `feat(movie): thêm tìm kiếm theo thể loại`, `fix(showtime): trả 204 cho OPTIONS`.
3. Trước khi mở PR: chạy service của mình + `python tests/integration/run_tests.py` (các service khác đang chạy).
4. Mở Pull Request vào `develop`, điền mẫu PR. **Cần 1 người khác duyệt**. Không tự merge PR của chính mình.
5. Không `git push --force` lên `develop`/`main`.

## 4. Khi làm việc chung
- Mỗi tuần một buổi **tích hợp**: cả nhóm chạy `scripts/start-all` và `INTEGRATION_CHECKLIST.md`.
- Phát hiện lỗi của service người khác: mở Issue có bước tái hiện, **không** sửa hộ.
- Báo nhóm trưởng ngay khi bị vướng — một người thiếu bài, cả nhóm bị trừ điểm.
