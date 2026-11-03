@echo off
rem Dùng nội bộ bởi start-all.bat / init-db.bat:  run-service.bat <tên> [--init-only | --force-init]
rem   <tên>: movie | showtime | user | booking | payment | notification   (thư mục services-py\<tên>)
rem Việc làm: tạo .venv (nếu chưa có) -> cài requirements.txt -> nạp .env của service -> tạo/nạp DB SQLite lần đầu -> chạy uvicorn.
rem   (không tham số)  tạo DB nếu file DB chưa có, rồi chạy service
rem   --init-only      chỉ tạo/nạp DB (idempotent) rồi thoát, KHÔNG chạy service
rem   --force-init     nạp lại dữ liệu mẫu (INSERT OR IGNORE, không ghi đè) rồi chạy service
rem Dời cổng (tuỳ chọn): đặt SOA_PORT_OFFSET=10000 để chạy ở 15001..15006 (vd. khi Windows giữ dải cổng 4922-5021).
rem   Lưu ý Admin/Client gọi cứng 5001..5006 nên chỉ dùng khi test bằng API.
setlocal EnableExtensions
set "NAME=%~1"
set "MODE=%~2"
if "%NAME%"=="" (
  echo Cach dung: run-service.bat ^<ten^> [--init-only ^| --force-init]
  exit /b 2
)
if "%SOA_PORT_OFFSET%"=="" set "SOA_PORT_OFFSET=0"

rem Cổng cố định theo API_CONTRACT (+ độ dời nếu có)
set /a P_MOVIE=5001+SOA_PORT_OFFSET
set /a P_SHOWTIME=5002+SOA_PORT_OFFSET
set /a P_USER=5003+SOA_PORT_OFFSET
set /a P_BOOKING=5004+SOA_PORT_OFFSET
set /a P_PAYMENT=5005+SOA_PORT_OFFSET
set /a P_NOTIFICATION=5006+SOA_PORT_OFFSET

set "PORT="
set "INIT="
rem Lệnh tạo/nạp DB của từng service (Showtime tạo bảng tự động khi dùng nên không cần)
if /i "%NAME%"=="movie"        ( set "PORT=%P_MOVIE%"        & set "INIT=-m app.db.seed" )
if /i "%NAME%"=="showtime"     ( set "PORT=%P_SHOWTIME%"     & set "INIT=-m app.db.seed" )
if /i "%NAME%"=="user"         ( set "PORT=%P_USER%"         & set "INIT=-m app.db.seed" )
if /i "%NAME%"=="booking"      ( set "PORT=%P_BOOKING%"      & set "INIT=-m app.db.init_db --seed" )
if /i "%NAME%"=="payment"      ( set "PORT=%P_PAYMENT%"      & set "INIT=-m app.db.init_db" )
if /i "%NAME%"=="notification" ( set "PORT=%P_NOTIFICATION%" & set "INIT=-m app.db.init_db --seed" )
if not defined PORT (
  echo [LOI] Ten service khong hop le: %NAME%
  exit /b 2
)

cd /d "%~dp0..\services-py\%NAME%" || (echo [LOI] Khong thay thu muc services-py\%NAME% & exit /b 1)
set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo [%NAME%] Tao moi truong ao .venv ...
  python -m venv .venv || (echo [LOI] Khong tao duoc .venv. Can Python 3.12 trong PATH. & exit /b 1)
)
echo [%NAME%] Kiem tra thu vien ...
"%PY%" -m pip install -q --disable-pip-version-check -r requirements.txt || (echo [LOI] Cai thu vien that bai & exit /b 1)

rem Nạp .env của service (bỏ dòng trống và dòng bắt đầu bằng #). KHÔNG commit .env.
if exist .env (
  for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
)

rem Cổng + địa chỉ các service khác (ghi đè .env để luôn khớp cổng đang dùng). 127.0.0.1 tránh chậm do localhost phân giải IPv6 trước.
set "HOST=0.0.0.0"
set "PORT=%PORT%"
set "PYTHONUTF8=1"
set "MOVIE_SERVICE_URL=http://127.0.0.1:%P_MOVIE%"
set "SHOWTIME_SERVICE_URL=http://127.0.0.1:%P_SHOWTIME%"
set "USER_SERVICE_URL=http://127.0.0.1:%P_USER%"
set "PAYMENT_SERVICE_URL=http://127.0.0.1:%P_PAYMENT%"
set "NOTIFICATION_SERVICE_URL=http://127.0.0.1:%P_NOTIFICATION%"
if not defined DB_PATH set "DB_PATH=%CD%\data\%NAME%.db"

set "DO_INIT="
if defined INIT (
  if /i "%MODE%"=="--init-only"  set "DO_INIT=1"
  if /i "%MODE%"=="--force-init" set "DO_INIT=1"
  if not exist "%DB_PATH%"       set "DO_INIT=1"
)
if defined DO_INIT (
  echo [%NAME%] Tao/nap DB: %DB_PATH%
  "%PY%" %INIT% || (echo [LOI] Tao/nap DB that bai & exit /b 1)
) else if /i "%MODE%"=="--init-only" (
  echo [%NAME%] Khong can nap DB ^(bang duoc tao tu dong khi dung^)
)
if /i "%MODE%"=="--init-only" exit /b 0

echo [%NAME%] Chay tai http://localhost:%PORT%  (Swagger: /docs)
"%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%
