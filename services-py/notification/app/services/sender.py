"""Gửi thông báo GIẢ LẬP: chỉ ghi dòng log, không gửi email/SMS thật."""
import logging

from app.entities.notification_log import NotificationLog

logger = logging.getLogger("notification")


class ConsoleSender:
    def send(self, n: NotificationLog) -> None:
        logger.info("SIMULATED channel=%s username=%r bookingId=%d message=%r",
                    n.channel, n.username, n.booking_id, n.message)
