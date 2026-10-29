# Kết quả xác minh thực tế

Ngày 03/10/2026, workspace Windows PowerShell `D:\workspace\SOA\project_final` ban đầu trống, không phải Git repo, không có AGENTS.md trong workspace/các thư mục cha đã kiểm tra. Không có service của thành viên khác được sửa.

## Đã chạy

- Tải Go chính thức từ go.dev vào `.tools/go`, kiểm tra SHA256 theo metadata chính thức. Phiên bản thực tế: go1.27.1 windows/amd64.
- `go mod tidy`: thành công; dependency trực tiếp duy nhất là go-sql-driver/mysql, edwards25519 là dependency gián tiếp của driver.
- `gofmt -w` với danh sách file PowerShell; `gofmt -l` không còn file chưa định dạng.
- `go vet ./...`: thành công.
- `go test ./... -count=1 -cover`: thành công, 0.914s, coverage tổng 57.0%. Bao phủ POST hợp lệ/chuẩn hóa/response, JSON sai/rỗng/null/array/trailing, validation Unicode/INT/channel, body quá lớn, trường message không được phép, method/Allow, route gần giống, OPTIONS, CORS success/lỗi, GET có dữ liệu/rỗng, sender/store lỗi. Test fake không kiểm tra MySQL thật.
- `go build ./...` và `go build -o bin/notification.exe .`: thành công.
- Chạy binary với DB_USER kiểm tra và không có MySQL: thoát mã 1, thông báo kết nối chung không lộ DSN/mật khẩu. Không mở API khi DB không sẵn sàng.
- `node --check` với script trích từ cả hai trang HTML: thành công.
- Python HTTP server cổng 8081; GET `/` và `/admin_notification.html` đều HTTP 200.

Lần chạy test đầu tiên bị Windows Application Control chặn executable tạm; các lần tiếp theo (bao gồm chạy không dùng cache ở trên) đã thành công. Không thay đổi chính sách bảo vệ Windows. Lệnh `gofmt *.go` không hoạt động trong PowerShell vì wildcard không được mở rộng cho executable; README dùng danh sách FullName đúng.

## Chưa xác minh do môi trường

Không tìm thấy Go/MySQL CLI trong PATH ban đầu, không có MySQL service hoặc listener cổng 3306. Docker CLI có sẵn nhưng engine chưa chạy. Chưa nạp schema/seed, chưa kiểm tra tính lặp lại của seed trên MySQL, chưa chạy GET/POST với database thật hoặc kiểm tra thứ tự SQL trong integration test. Không tự tạo tài khoản DB hoặc sửa dịch vụ hệ thống. Runtime vẫn dùng MySQL thật, không thay bằng fake.

Công cụ browser trả không có browser khả dụng; chưa kiểm tra trực quan, trạng thái bảng/filter qua trình duyệt, responsive hoặc browser console. HTTP 200 và node syntax check không thay thế kiểm thử trình duyệt.

## Kiểm tra lại khi môi trường sẵn sàng

1. Thực thi db/schema.sql và db/seed.sql theo README. Chạy seed hai lần; GET/log hoặc SQL phải chỉ có một dòng mẫu tương ứng, không mất dữ liệu cũ.
2. Cấu hình DB_USER/DB_PASSWORD qua môi trường, `go run .` phải kết nối thành công.
3. GET `/api/notify/logs` thấy seed; POST hợp lệ tạo ID mới; GET thấy ID đó và mới nhất trước.
4. Mở admin ở 8081, bấm Tải lại; kiểm tra lọc username/bookingId/channel, không có kết quả, console và màn hình hẹp.
5. Dừng API rồi Tải lại để kiểm tra thông báo mất kết nối. Khởi động lại API và Tải lại để phục hồi.
6. Ctrl+C kiểm tra server dừng và cổng 5006 được giải phóng. Không xóa log có sẵn khi kiểm thử.

Chưa có 5 trang admin còn lại hoặc 6 báo cáo nhóm; khung hiện chỉ tích hợp Notification, các tab còn lại ghi Chưa tích hợp. Các nâng cấp cuối kỳ ghi riêng trong final-term-plan.md, chưa triển khai.
