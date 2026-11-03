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

# VNPAY Sandbox (thanh toán thử). Lấy từ env/.env — KHÔNG commit khóa thật (xem .env.example).
VNPAY_TMN_CODE = os.environ.get("VNPAY_TMN_CODE", "")
VNPAY_HASH_SECRET = os.environ.get("VNPAY_HASH_SECRET", "")
VNPAY_URL = os.environ.get("VNPAY_URL", "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")
# URL mà trình duyệt được VNPAY chuyển về sau khi thanh toán (phải truy cập được từ máy người dùng)
VNPAY_RETURN_URL = os.environ.get("VNPAY_RETURN_URL", f"http://localhost:{PORT}/api/payment/vnpay/return")
# Trang Client để đưa người dùng quay lại sau khi VNPAY trả kết quả
CLIENT_URL = os.environ.get("CLIENT_URL", "http://localhost:8080")
