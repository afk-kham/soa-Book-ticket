@echo off
rem Dừng các cửa sổ do start-all.bat mở (theo tên cửa sổ "SOA ..."), kèm tiến trình con của chúng.
rem Chỉ động tới cửa sổ có tên bắt đầu bằng "SOA ". Cách khác: đóng từng cửa sổ.
set "FOUND="
for %%t in ("SOA Movie" "SOA Showtime" "SOA User" "SOA Booking" "SOA Payment" "SOA Notification" "SOA Admin" "SOA Client") do (
  rem taskkill luôn trả mã 0 kể cả khi không có cửa sổ nào khớp, nên dò bằng tasklist trước
  tasklist /FI "WINDOWTITLE eq %%~t*" 2>nul | find /i "cmd.exe" >nul && (
    taskkill /F /T /FI "WINDOWTITLE eq %%~t*" >nul 2>nul
    echo da dung %%~t
    set "FOUND=1"
  )
)
if not defined FOUND echo Khong co cua so "SOA ..." nao dang chay.
echo Xong.
