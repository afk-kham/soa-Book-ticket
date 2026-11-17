"""Nghiệp vụ Notification: kiểm tra dữ liệu, sinh nội dung, điều phối repository/sender.

Không biết HTTP (chỉ ném ApiError) và không viết SQL. Thông báo lỗi giữ nguyên như mã Go cũ.
"""
import logging
import re
import smtplib
from datetime import datetime, timezone

from app.core.errors import ApiError
from app.entities.notification_log import NotificationLog
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import CreateLogRequest, NotifyRequest, OtpNotifyRequest, UpdateLogRequest
from app.services.sender import SENT, ConsoleSender, DeliverySender

logger = logging.getLogger("notification")

MAX_BOOKING_ID = 2147483647
CHANNELS = ("EMAIL", "SMS")
_STORE_ERRORS = {
    "ghi": "Không thể lưu nhật ký thông báo",
    "đọc": "Không thể đọc nhật ký thông báo",
    "sửa": "Không thể cập nhật nhật ký thông báo",
    "xóa": "Không thể xóa nhật ký thông báo",
}


EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
OTP_RE = re.compile(r"[0-9]{4,8}")


def compose_message(booking_id: int) -> str:
    return f"Đặt vé thành công cho đơn #{booking_id}"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")



def _check_booking_id(booking_id: int) -> None:
    if booking_id <= 0 or booking_id > MAX_BOOKING_ID:
        raise ApiError(400, "bookingId phải là số nguyên dương")


def _check_channel(channel: str) -> None:
    if channel not in CHANNELS:
        raise ApiError(400, "channel phải là EMAIL hoặc SMS")


class NotificationService:
    def __init__(self, repo: NotificationRepository | None = None, sender: DeliverySender | None = None):
        self.repo = repo or NotificationRepository()
        self.sender = sender or DeliverySender()

    def _store(self, action: str, fn, *args):
        """Gọi repository; lỗi CSDL được ghi log nội bộ và đổi thành 500 (không lộ chi tiết SQL)."""
        try:
            return fn(*args)
        except Exception:
            logger.exception("Thao tác CSDL '%s' thất bại", action)
            raise ApiError(500, _STORE_ERRORS[action])

    # POST /api/notify
    def notify(self, req: NotifyRequest) -> NotificationLog:
        username, channel = req.username.strip(), req.channel.strip().upper()
        _check_booking_id(req.booking_id)
        if username == "" or len(username) > 50:
            raise ApiError(400, "username phải có từ 1 đến 50 ký tự Unicode")
        _check_channel(channel)
        email = (req.email or "").strip()
        if email and (len(email) > 100 or not EMAIL_RE.fullmatch(email)):
            raise ApiError(400, "email không hợp lệ")
        n = NotificationLog(0, req.booking_id, username, channel, compose_message(req.booking_id), now_utc())
        body = f"Xin chào {username},\n\n{n.message}.\n\nCảm ơn bạn đã đặt vé tại SOA Cinema."
        n.delivery = self._deliver(n, email, f"SOA Cinema - Xác nhận đặt vé #{n.booking_id}", body)
        n.id = self._store("ghi", self.repo.insert, n.booking_id, n.username, n.channel, n.message, n.sent_at)
        return n

    # POST /api/notify/otp
    def send_otp(self, req: OtpNotifyRequest) -> NotificationLog:
        """Gửi mã OTP thanh toán qua email. Nhật ký KHÔNG lưu mã (chỉ ghi đã gửi)."""
        username, email, otp = req.username.strip(), req.email.strip(), req.otp.strip()
        _check_booking_id(req.booking_id)
        if username == "" or len(username) > 50:
            raise ApiError(400, "username phải có từ 1 đến 50 ký tự Unicode")
        if not email or len(email) > 100 or not EMAIL_RE.fullmatch(email):
            raise ApiError(400, "email không hợp lệ")
        if not OTP_RE.fullmatch(otp):
            raise ApiError(400, "otp phải gồm 4 đến 8 chữ số")
        if not 30 <= req.ttl_seconds <= 3600:
            raise ApiError(400, "ttlSeconds phải từ 30 đến 3600")
        n = NotificationLog(0, req.booking_id, username, "EMAIL",
                            f"Đã gửi mã OTP xác nhận thanh toán cho đơn #{req.booking_id}", now_utc())
        body = (f"Xin chào {username},\n\nMã OTP xác nhận thanh toán đơn #{req.booking_id} của bạn là: {otp}\n"
                f"Mã có hiệu lực trong {req.ttl_seconds // 60} phút. Không chia sẻ mã này cho bất kỳ ai.\n\nSOA Cinema")
        n.delivery = self._deliver(n, email, f"SOA Cinema - Mã OTP thanh toán đơn #{req.booking_id}", body)
        if n.delivery != SENT:  # chỉ ở chế độ giả lập: in mã ra log để demo/kiểm thử (không lưu DB)
            logger.info("SIMULATED OTP bookingId=%d email=%s otp=%s", req.booking_id, email, otp)
        n.id = self._store("ghi", self.repo.insert, n.booking_id, n.username, n.channel, n.message, n.sent_at)
        return n

    def _deliver(self, n: NotificationLog, email: str, subject: str, body: str) -> str:
        try:
            return self.sender.deliver(n, email or None, subject, body)
        except (smtplib.SMTPException, OSError):
            logger.exception("Gửi email thất bại")
            raise ApiError(500, "Không gửi được email")
        except Exception:
            logger.exception("Gửi thông báo thất bại")
            raise ApiError(500, "Không thể xử lý thông báo")

    # GET /api/notify/logs
    def list_logs(self, booking_id: str | None, username: str | None, channel: str | None) -> list[NotificationLog]:
        bid = None
        if booking_id not in (None, ""):
            if not re.fullmatch(r"[0-9]+", booking_id) or not 0 < int(booking_id) <= MAX_BOOKING_ID:
                raise ApiError(400, "bookingId phải là số nguyên dương")
            bid = int(booking_id)
        ch = (channel or "").strip().upper()
        if ch and ch not in CHANNELS:
            raise ApiError(400, "channel phải là EMAIL hoặc SMS")
        return self._store("đọc", self.repo.list, bid, (username or "").strip(), ch)

    # GET /api/notify/logs/{id}
    def get_log(self, log_id: int) -> NotificationLog:
        n = self._store("đọc", self.repo.get, log_id)
        if n is None:
            raise ApiError(404, "Không tìm thấy nhật ký thông báo")
        return n

    # POST /api/notify/logs
    def create_log(self, req: CreateLogRequest) -> NotificationLog:
        username, message, channel = req.username.strip(), req.message.strip(), req.channel.strip().upper()

        _check_booking_id(req.booking_id)
        _check_channel(channel)
        if username == "" or len(username) > 50:
            raise ApiError(400, "username phải có từ 1 đến 50 ký tự Unicode")
        if message == "":
            message = compose_message(req.booking_id)
        elif len(message) > 255:
            raise ApiError(400, "message tối đa 255 ký tự")

        n = NotificationLog(0, req.booking_id, username, channel, message, now_utc())
        n.id = self._store("ghi", self.repo.insert, n.booking_id, n.username, n.channel, n.message, n.sent_at)
        return n

    # PUT|PATCH /api/notify/logs/{id}
    def update_log(self, log_id: int, req: UpdateLogRequest) -> NotificationLog:
        username, message = req.username, req.message
        if username is not None:
            username = username.strip()
            if username == "" or len(username) > 50:
                raise ApiError(400, "Người nhận không được để trống và tối đa 50 ký tự")
        channel = None
        if req.channel is not None:
            channel = req.channel.strip().upper()
            _check_channel(channel)

        existing = None
        if message is not None:
            existing = self._store("đọc", self.repo.get, log_id)
            if existing is None:
                raise ApiError(404, "Không tìm thấy nhật ký thông báo để cập nhật")

        if req.booking_id is not None:
            _check_booking_id(req.booking_id)

        if message is not None:
            message = message.strip()
            if existing is not None and existing.booking_id == 0:  # nhật ký thử nghiệm cũ giữ tiền tố
                message = message.removeprefix("[Thử nghiệm] ")
                if message == "" or len(message) > 242:
                    raise ApiError(400, "Nội dung thử nghiệm phải có tối đa 242 ký tự")
                message = "[Thử nghiệm] " + message
            if message == "" or len(message) > 255:
                raise ApiError(400, "message không được rỗng và tối đa 255 ký tự")

        fields = {k: v for k, v in (("username", username), ("channel", channel), ("message", message),
                                    ("booking_id", req.booking_id)) if v is not None}
        updated = self._store("sửa", self.repo.update, log_id, fields)
        if updated is None:
            raise ApiError(404, "Không tìm thấy nhật ký thông báo để cập nhật")
        return updated

    # DELETE /api/notify/logs/{id}
    def delete_log(self, log_id: int) -> None:
        if not self._store("xóa", self.repo.delete, log_id):
            raise ApiError(404, "Không tìm thấy nhật ký thông báo để xóa")

    # GET /api/notify/logs/find?keyword=
    def find_key_word(self, keyword: str) -> list[NotificationLog]:
        keyword = keyword.strip()
        if keyword == "":
            raise ApiError(400, "Từ khóa tìm kiếm không được để trống")
        return self._store("đọc", self.repo.find_key_word, keyword)
