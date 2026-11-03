@echo off
rem Tạo/nạp lại DB SQLite cho các service Python (schema + dữ liệu mẫu). Idempotent: INSERT OR IGNORE, KHÔNG xóa dữ liệu có sẵn.
rem Chạy từ thư mục gốc:  scripts\init-db.bat
rem (start-all.bat tự tạo DB lần đầu; chỉ cần chạy file này khi muốn nạp lại dữ liệu mẫu. Cần .venv: chạy start-all một lần trước,
rem  hoặc file này sẽ tự tạo .venv + cài thư viện.)
setlocal
cd /d "%~dp0.."
for %%s in (movie user booking payment notification) do (
  echo ^>^> %%s
  call scripts\run-service.bat %%s --init-only || goto :err
)
echo OK: da tao/nap DB SQLite (services-py\^<ten^>\data\^<ten^>.db).
echo Showtime tao bang tu dong khi dung; lich chieu 7 ngay toi do Showtime tu sinh.
exit /b 0
:err
echo LOI khi tao/nap DB. Xem thong bao phia tren.
exit /b 1
