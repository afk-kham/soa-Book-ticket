"""Nghiệp vụ Notification: kiểm tra dữ liệu, sinh nội dung, điều phối repository/sender.

Không biết HTTP (chỉ ném ApiError) và không viết SQL. Thông báo lỗi giữ nguyên như mã Go cũ.
"""
import logging
import re
from datetime import datetime, timezone

from app.core.errors import ApiError
from app.entities.notification_log import NotificationLog
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import CreateLogRequest, NotifyRequest, UpdateLogRequest
from app.services.sender import ConsoleSender

logger = logging.getLogger("notification")

MAX_BOOKING_ID = 2147483647
CHANNELS = ("EMAIL", "SMS")
_EMAIL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
                    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+$")
_PHONE = re.compile(r"^[0-9]{9,15}$")
_STORE_ERRORS = {
    "ghi": "Không thể lưu nhật ký thông báo",
    "đọc": "Không thể đọc nhật ký thông báo",
    "sửa": "Không thể cập nhật nhật ký thông báo",
    "xóa": "Không thể xóa nhật ký thông báo",
}


def compose_message(booking_id: int) -> str:
    return f"Đặt vé thành công cho đơn #{booking_id}"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_recipient(channel: str, recipient: str) -> None:
    if recipient == "" or len(recipient) > 50:
        raise ApiError(400, "Vui lòng nhập người nhận (tối đa 50 ký tự)")
    if channel == "EMAIL":
        if not _EMAIL.match(recipient):
            raise ApiError(400, "Vui lòng nhập địa chỉ email hợp lệ")
    elif channel == "SMS":
        if not _PHONE.match(recipient.removeprefix("+")):
            raise ApiError(400, "Vui lòng nhập số điện thoại hợp lệ (9–15 chữ số)")
    else:
        raise ApiError(400, "channel phải là EMAIL hoặc SMS")


def _check_booking_id(booking_id: int) -> None:
    if booking_id <= 0 or booking_id > MAX_BOOKING_ID:
        raise ApiError(400, "bookingId phải là số nguyên dương trong phạm vi INT MySQL")


def _check_channel(channel: str) -> None:
    if channel not in CHANNELS:
        raise ApiError(400, "channel phải là EMAIL hoặc SMS")


class NotificationService:
    def __init__(self, repo: NotificationRepository | None = None, sender: ConsoleSender | None = None):
        self.repo = repo or NotificationRepository()
        self.sender = sender or ConsoleSender()

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
        n = NotificationLog(0, req.booking_id, username, channel, compose_message(req.booking_id), now_utc())
        try:
            self.sender.send(n)
        except Exception:
            logger.exception("Gửi giả lập thất bại")
            raise ApiError(500, "Không thể xử lý thông báo")
        n.id = self._store("ghi", self.repo.insert, n.booking_id, n.username, n.channel, n.message, n.sent_at)
        return n

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
        username, message = req.username, req.message
        new_recipient = req.recipient != ""
        if new_recipient:
            if username != "":
                raise ApiError(400, "Chỉ gửi một trong hai trường recipient hoặc username")
            username = req.recipient
        if req.content != "":
            if message != "":
                raise ApiError(400, "Chỉ gửi một trong hai trường content hoặc message")
            message = req.content
        username, message, channel = username.strip(), message.strip(), req.channel.strip().upper()

        _check_booking_id(req.booking_id)
        _check_channel(channel)
        if new_recipient:
            validate_recipient(channel, username)
        elif username == "" or len(username) > 50:
            raise ApiError(400, "username phải có từ 1 đến 50 ký tự Unicode")
        if message == "":
            if new_recipient:
                raise ApiError(400, "Vui lòng nhập nội dung thông báo")
            message = compose_message(req.booking_id)
        elif len(message) > 255:
            raise ApiError(400, "message tối đa 255 ký tự")

        n = NotificationLog(0, req.booking_id, username, channel, message, now_utc())
        n.id = self._store("ghi", self.repo.insert, n.booking_id, n.username, n.channel, n.message, n.sent_at)
        return n

    # PUT|PATCH /api/notify/logs/{id}
    def update_log(self, log_id: int, req: UpdateLogRequest) -> NotificationLog:
        username, message = req.username, req.message
        new_recipient = req.recipient is not None
        if new_recipient:
            if username is not None:
                raise ApiError(400, "Chỉ gửi một trong hai trường recipient hoặc username")
            username = req.recipient
        if req.content is not None:
            if message is not None:
                raise ApiError(400, "Chỉ gửi một trong hai trường content hoặc message")
            message = req.content

        if username is not None:
            username = username.strip()
            if username == "" or len(username) > 50:
                raise ApiError(400, "Người nhận không được để trống và tối đa 50 ký tự")
        channel = None
        if req.channel is not None:
            channel = req.channel.strip().upper()
            _check_channel(channel)

        existing = None
        if new_recipient or channel is not None or message is not None:
            existing = self._store("đọc", self.repo.get, log_id)
            if existing is None:
                raise ApiError(404, "Không tìm thấy nhật ký thông báo để cập nhật")
            if new_recipient:
                validate_recipient(channel or existing.channel, username)

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
