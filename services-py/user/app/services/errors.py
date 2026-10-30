"""Lỗi nghiệp vụ của User Service. Service KHÔNG biết HTTP - Controller dịch các lỗi này ra mã HTTP."""


class UserServiceError(Exception):
    """Lớp cơ sở cho lỗi nghiệp vụ."""


class UsernameTakenError(UserServiceError):
    """Username đã tồn tại (-> 409 CONFLICT)."""


class InvalidCredentialsError(UserServiceError):
    """Sai tên đăng nhập hoặc mật khẩu (-> 401 UNAUTHORIZED). Dùng CHUNG cho cả hai trường hợp."""


class UserNotFoundError(UserServiceError):
    """Không tìm thấy người dùng (-> 404 NOT_FOUND)."""
