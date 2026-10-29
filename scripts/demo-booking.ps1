# Demo API Booking Service (bản tích hợp) trên Windows PowerShell — dùng curl.exe, không dùng alias curl.
# Cần chạy đủ 6 service (scripts\start-all.bat) trên CSDL vừa nạp bằng scripts\init-db.bat.
# Chạy:  powershell -ExecutionPolicy Bypass -File .\scripts\demo-booking.ps1
# Dựa trên demo_api.ps1 của TV4 (bản giữa kỳ: docs/tv4-booking/source-giua-ky/demo_api.ps1).
# Lưu ý: bước đặt ghế trống (A3, A4) chỉ thành công lần đầu; chạy lại sẽ nhận 409 SEAT_TAKEN (đúng nghiệp vụ).
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$base = "http://localhost:5004"
$tmp = Join-Path $env:TEMP "booking_body.json"

function Step($title) { Write-Host "`n===== $title" -ForegroundColor Cyan }
function Post($json) {
    # Ghi body ra file UTF-8 không BOM rồi gửi, tránh lỗi dấu nháy khi truyền JSON cho curl.exe
    [IO.File]::WriteAllText($tmp, $json)
    curl.exe -s -i -X POST "$base/api/booking" -H "Content-Type: application/json" --data-binary "@$tmp"
    Write-Host ""
}

Step "OPTIONS /api/booking -> 204 + CORS"
curl.exe -s -i -X OPTIONS "$base/api/booking"

Step "GET /api/booking -> 200 danh sách đơn"
curl.exe -s "$base/api/booking"

Step "GET /api/booking/seats?showtimeId=1 -> 200 các ghế đã giữ"
curl.exe -s "$base/api/booking/seats?showtimeId=1"

Step "POST ghế A1, A2 suất 1 -> 409 SEAT_TAKEN (đã thuộc đơn #1 PAID)"
Post '{"username":"user1","movieId":1,"showtimeId":1,"seats":["A1","A2"],"paymentMethod":"MOMO"}'

Step "POST ghế trống A3, A4 -> 201 (User -> Movie -> Showtime -> Payment -> Notification)"
Post '{"username":"user1","movieId":1,"showtimeId":1,"seats":["A3","A4"],"paymentMethod":"MOMO"}'

Step "POST ghế B5 của đơn #2 đã CANCELLED -> 201 (ghế đã được nhả)"
Post '{"username":"user2","movieId":2,"showtimeId":3,"seats":["B5"],"paymentMethod":"CASH"}'

Step "GET /api/booking/1 -> 200"
curl.exe -s "$base/api/booking/1"

Step "GET /api/booking/99999 -> 404 NOT_FOUND"
curl.exe -s -i "$base/api/booking/99999"

Step "POST dữ liệu sai -> 400 VALIDATION_ERROR"
Post '{"username":"user1","movieId":0,"showtimeId":1,"seats":["A1","a1","K100"]}'

Step "DELETE /api/booking/1 -> 405 METHOD_NOT_ALLOWED"
curl.exe -s -i -X DELETE "$base/api/booking/1"
