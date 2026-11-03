"""Đồng hồ của Booking: mọi mốc thời gian đều theo APP_TIMEZONE, không theo giờ máy.

Container Python chạy UTC trong khi giờ chiếu của Showtime và trình duyệt theo giờ Việt Nam.
Dùng giờ máy sẽ lệch 7 tiếng: khách vừa giữ ghế đã thấy hết hạn, suất đã chiếu vẫn đặt được.
"""
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core import config

logger = logging.getLogger("booking-service")

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _timezone() -> ZoneInfo | timezone:
    try:
        return ZoneInfo(config.APP_TIMEZONE)
    except ZoneInfoNotFoundError:
        if config.APP_TIMEZONE != "Asia/Ho_Chi_Minh":
            raise
        logger.debug("Không tìm thấy timezone database; dùng UTC+07:00 cho Asia/Ho_Chi_Minh")
        return timezone(timedelta(hours=7))


def now() -> datetime:
    """Giờ hiện tại làm tròn tới giây (không kèm tzinfo, cùng dạng cột created_at)."""
    return datetime.now(_timezone()).replace(tzinfo=None, microsecond=0)


def format_time(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)
