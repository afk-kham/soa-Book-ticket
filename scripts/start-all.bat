@echo off
rem Chạy cả 6 service + Admin + Client, mỗi cái một cửa sổ riêng. Đóng cửa sổ để dừng service đó.
rem Cần: python, php, java 17+ & maven, dotnet 8, node, go, MySQL, MongoDB.
cd /d "%~dp0.."
start "Movie 5001"        cmd /k scripts\run-service.bat services\movie python movie_service.py
start "Showtime 5002"     cmd /k scripts\run-service.bat services\showtime php -S 0.0.0.0:5002 router.php
start "User 5003"         cmd /k scripts\run-service.bat services\user mvn -q compile exec:java
start "Booking 5004"      cmd /k scripts\run-service.bat services\booking dotnet run
start "Payment 5005"      cmd /k scripts\run-service.bat services\payment node payment_service.js
start "Notification 5006" cmd /k scripts\run-service.bat services\notification go run .
start "Admin 8081"        cmd /k scripts\run-service.bat admin python -m http.server 8081
start "Client 8080"       cmd /k scripts\run-service.bat client python -m http.server 8080
echo Admin: http://localhost:8081   Client: http://localhost:8080
echo Kiem tra: python tests\integration\run_tests.py
