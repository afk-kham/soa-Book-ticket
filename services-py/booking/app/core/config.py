"""Cấu hình Booking Service - đọc từ biến môi trường (không hard-code).

Chỉ thêm biến mới khi đã ghi vào .env.example và README.md của service.
"""
import os

SERVICE_NAME = "booking-service"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5004"))

# SQLite: MỖI service một file riêng (database-per-service). Trong Docker: /data/<tên>.db (volume).
DB_PATH = os.environ.get("DB_PATH", "./data/booking.db")

# Biến riêng của service (URL service khác đọc từ env, KHÔNG hard-code rải rác trong source)
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://user:5003")
MOVIE_SERVICE_URL = os.environ.get("MOVIE_SERVICE_URL", "http://movie:5001")
SHOWTIME_SERVICE_URL = os.environ.get("SHOWTIME_SERVICE_URL", "http://showtime:5002")
PAYMENT_SERVICE_URL = os.environ.get("PAYMENT_SERVICE_URL", "http://payment:5005")
NOTIFICATION_SERVICE_URL = os.environ.get("NOTIFICATION_SERVICE_URL", "http://notification:5006")
UPSTREAM_TIMEOUT_SECONDS = int(os.environ.get("UPSTREAM_TIMEOUT_SECONDS", "5"))
HOLD_MINUTES = int(os.environ.get("HOLD_MINUTES", "10"))
JWT_SECRET = os.environ.get("JWT_SECRET", "")
INTERNAL_KEY = os.environ.get("INTERNAL_KEY", "")
