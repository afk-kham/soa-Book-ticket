import os


def _load_dotenv(path=".env"):
    """Đọc file .env (KEY=VALUE) nếu có; biến môi trường hệ điều hành luôn được ưu tiên."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

# Cấu hình CSDL MySQL cho Movie Service (tên biến dùng CHUNG cho cả 6 service)
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")  # XAMPP/WAMP thường để trống; KHÔNG commit mật khẩu thật
DB_NAME = os.environ.get("DB_NAME", "movie_db")
DB_CHARSET = "utf8mb4"

# Cấu hình máy chủ HTTP Movie Service (theo hợp đồng SOA: cổng 5001)
SERVER_HOST = os.environ.get("HOST", os.environ.get("SERVER_HOST", "0.0.0.0"))
SERVER_PORT = int(os.environ.get("PORT", os.environ.get("SERVER_PORT", 5001)))
