"""Lỗi nghiệp vụ của Booking Service (thay ApiException của Models.cs).

Lỗi chỉ mang mã lỗi + thông báo, không biết HTTP: Controller dịch mã lỗi ra mã HTTP.
"""


class BookingError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validation_error(message: str) -> BookingError:
    return BookingError("VALIDATION_ERROR", message)
