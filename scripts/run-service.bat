@echo off
rem Dùng nội bộ bởi start-all.bat:  run-service.bat <thư mục service> <lệnh...>
rem Nạp .env của service (bỏ dòng trống và dòng bắt đầu bằng #) rồi chạy lệnh.
setlocal EnableDelayedExpansion
set "DIR=%~1"
set "CMD="
for /f "tokens=1,* delims= " %%a in ("%*") do set "CMD=%%b"
cd /d "%~dp0..\%DIR%"
if exist .env (
  for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
)
%CMD%
