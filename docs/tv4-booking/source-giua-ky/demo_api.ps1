# Demo API Booking Service trên Windows PowerShell (dùng curl.exe, không dùng alias curl).
# Chạy:  powershell -ExecutionPolicy Bypass -File .\demo_api.ps1
# Để có kết quả giống báo cáo, chạy trên CSDL vừa nạp schema.sql + seed.sql.
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

Step "POST lệnh mẫu của phiếu (A1, A2 suất 1) -> 400 vì trùng đơn #1"
Post '{"movieId":1,"showtimeId":1,"seats":["A1","A2"],"pricePerSeat":90000,"username":"user1"}'

Step "POST ghế trống A3, A4 -> 201"
Post '{"movieId":1,"showtimeId":1,"seats":["A3","A4"],"pricePerSeat":90000,"username":"user1"}'

Step "POST ghế B5 của đơn #2 đã CANCELLED -> 201"
Post '{"movieId":2,"showtimeId":3,"seats":["B5"],"pricePerSeat":85000,"username":"user2"}'

Step "GET /api/booking/1 -> 200"
curl.exe -s "$base/api/booking/1"

Step "GET /api/booking/99 -> 404"
curl.exe -s -i "$base/api/booking/99"

Step "POST dữ liệu sai -> 400"
Post '{"movieId":0,"showtimeId":1,"seats":["A1","a1","K100"],"pricePerSeat":-5}'

Step "DELETE /api/booking/1 -> 405"
curl.exe -s -i -X DELETE "$base/api/booking/1"
