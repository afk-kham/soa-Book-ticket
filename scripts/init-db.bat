@echo off
rem Tạo 5 CSDL MySQL (schema + seed). Chạy từ thư mục gốc:  scripts\init-db.bat
rem Đặt DB_USER / DB_PASSWORD trước nếu không dùng root không mật khẩu.
setlocal
cd /d "%~dp0.."
if "%DB_USER%"=="" set DB_USER=root
set PW=
if not "%DB_PASSWORD%"=="" set PW=-p%DB_PASSWORD%
for %%s in (movie showtime user booking notification) do (
  echo ^>^> %%s_db
  mysql -u%DB_USER% %PW% --default-character-set=utf8mb4 < database\%%s\schema.sql || goto :err
  mysql -u%DB_USER% %PW% --default-character-set=utf8mb4 < database\%%s\seed.sql || goto :err
)
echo OK: da nap 5 CSDL MySQL.
echo Payment (MongoDB): mongosh database\payment\seed.js
exit /b 0
:err
echo LOI khi nap CSDL. Kiem tra MySQL dang chay va DB_USER / DB_PASSWORD.
exit /b 1
