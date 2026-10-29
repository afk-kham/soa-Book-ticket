"""Cấu hình Payment Service - đọc từ biến môi trường (không hard-code).

Chỉ thêm biến mới khi đã ghi vào .env.example và README.md của service.
"""
import os

SERVICE_NAME = "payment-service"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5005"))

# SQLite: MỖI service một file riêng (database-per-service). Trong Docker: /data/<tên>.db (volume).
DB_PATH = os.environ.get("DB_PATH", "./data/payment.db")

# Biến riêng của service (URL service khác đọc từ env, KHÔNG hard-code rải rác trong source)
JWT_SECRET = os.environ.get("JWT_SECRET", "")
