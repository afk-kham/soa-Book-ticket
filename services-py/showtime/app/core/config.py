"""Cấu hình Showtime Service - đọc từ biến môi trường (không hard-code).

Chỉ thêm biến mới khi đã ghi vào .env.example và README.md của service.
"""
import os

SERVICE_NAME = "showtime-service"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5002"))

# SQLite: MỖI service một file riêng (database-per-service). Trong Docker: /data/<tên>.db (volume).
DB_PATH = os.environ.get("DB_PATH", "./data/showtime.db")

# Biến riêng của service (URL service khác đọc từ env, KHÔNG hard-code rải rác trong source)
MOVIE_SERVICE_URL = os.environ.get("MOVIE_SERVICE_URL", "http://movie:5001")
VALIDATE_MOVIE = os.environ.get("VALIDATE_MOVIE", "true").strip().lower() != "false"
AUTO_SCHEDULE_DAYS = int(os.environ.get("AUTO_SCHEDULE_DAYS", "7"))
APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "Asia/Ho_Chi_Minh")
JWT_SECRET = os.environ.get("JWT_SECRET", "")
