@echo off
rem Chạy cả 6 service Python (services-py) + Admin (8081) + Client (8080), mỗi cái một cửa sổ riêng. Đóng cửa sổ để dừng.
rem Cần: Python 3.12 trong PATH. Lần đầu mỗi service tự tạo .venv, cài thư viện và tạo DB SQLite (services-py\<tên>\data\<tên>.db).
rem Dừng tất cả:  scripts\stop-all.bat      Nạp lại dữ liệu mẫu:  scripts\init-db.bat
cd /d "%~dp0.."

rem Nạp lại PATH mới nhất từ hệ thống: terminal mở trước khi cài Python (vd. terminal trong VS Code) vẫn giữ PATH cũ.
for /f "usebackq delims=" %%p in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')"`) do set "PATH=%%p"

where python >nul 2>nul || (
  echo [LOI] Chua tim thay python trong PATH. Cai Python 3.12 roi chay lai.
  exit /b 1
)

start "SOA Movie 5001"        cmd /k scripts\run-service.bat movie
start "SOA Showtime 5002"     cmd /k scripts\run-service.bat showtime
start "SOA User 5003"         cmd /k scripts\run-service.bat user
start "SOA Booking 5004"      cmd /k scripts\run-service.bat booking
start "SOA Payment 5005"      cmd /k scripts\run-service.bat payment
start "SOA Notification 5006" cmd /k scripts\run-service.bat notification
start "SOA Admin 8081"        cmd /k "cd /d admin && python -m http.server 8081"
start "SOA Client 8080"       cmd /k "cd /d client && python -m http.server 8080"
echo.
echo Admin: http://localhost:8081   Client: http://localhost:8080
echo Swagger moi service: http://localhost:500x/docs   (lan dau cho ~1 phut de cai thu vien)
echo Kiem tra: python tests\integration\run_tests.py
