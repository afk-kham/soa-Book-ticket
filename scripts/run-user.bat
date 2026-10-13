@echo off
rem Dùng nội bộ bởi start-all.bat (thư mục hiện tại là services\user, .env đã được nạp).
rem Không dùng "mvn exec:java": plugin chạy app trong classloader riêng nên DriverManager báo
rem "No suitable driver" với MySQL Connector/J. Thay vào đó Maven chỉ build classpath, rồi chạy bằng java.
call mvn -q compile dependency:build-classpath -Dmdep.outputFile=target\cp.txt || exit /b 1
set "CP="
for /f "usebackq delims=" %%c in ("target\cp.txt") do set "CP=%%c"
java -cp "target\classes;%CP%" userservice.Main
