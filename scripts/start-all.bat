@echo off
rem Chạy cả 6 service + Admin + Client, mỗi cái một cửa sổ riêng. Đóng cửa sổ để dừng service đó.
rem Cần: python, php 8.1+, java 17+ & maven, dotnet 8 SDK, node, go, MySQL, MongoDB.
cd /d "%~dp0.."

rem Nạp lại PATH mới nhất từ hệ thống: terminal mở trước khi cài PHP/Maven (vd. terminal trong VS Code) vẫn giữ PATH cũ.
for /f "usebackq delims=" %%p in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')"`) do set "PATH=%%p"

rem Báo trước công cụ còn thiếu (service tương ứng sẽ không chạy được).
set MISSING=
for %%c in (python php java mvn dotnet node go) do (
  where %%c >nul 2>nul || call set "MISSING=%%MISSING%% %%c"
)
if defined MISSING echo [CANH BAO] Chua tim thay trong PATH:%MISSING%

start "Movie 5001"        cmd /k scripts\run-service.bat services\movie python movie_service.py
start "Showtime 5002"     cmd /k scripts\run-service.bat services\showtime php -S 0.0.0.0:5002 router.php
start "User 5003"         cmd /k scripts\run-service.bat services\user ..\..\scripts\run-user.bat
start "Booking 5004"      cmd /k scripts\run-service.bat services\booking dotnet run
start "Payment 5005"      cmd /k scripts\run-service.bat services\payment node payment_service.js
start "Notification 5006" cmd /k scripts\run-service.bat services\notification go run .
start "Admin 8081"        cmd /k scripts\run-service.bat admin python -m http.server 8081
start "Client 8080"       cmd /k scripts\run-service.bat client python -m http.server 8080
echo Admin: http://localhost:8081   Client: http://localhost:8080
echo Kiem tra: python tests\integration\run_tests.py
