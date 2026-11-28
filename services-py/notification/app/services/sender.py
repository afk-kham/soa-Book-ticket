"""Gửi thông báo qua Email thật (SMTP) khi có cấu hình SMTP_HOST; ngược lại chỉ giả lập (ghi log).

Lỗi SMTP được ném cho người gọi (smtplib.SMTPException / OSError) để quyết định xử lý.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core import config
from app.entities.notification_log import NotificationLog

logger = logging.getLogger("notification")

SENT = "SENT"
SIMULATED = "SIMULATED"


class ConsoleSender:
    """Chỉ ghi dòng log (không gửi gì)."""

    def send(self, n: NotificationLog) -> None:
        logger.info("SIMULATED channel=%s username=%r bookingId=%d message=%r",
                    n.channel, n.username, n.booking_id, n.message)


class DeliverySender(ConsoleSender):
    """Email thật nếu SMTP đã cấu hình và có địa chỉ nhận; còn lại giả lập."""

    def smtp_enabled(self) -> bool:
        return bool(config.SMTP_HOST)

    def deliver(self, n: NotificationLog, email: str | None = None, subject: str | None = None,
                body: str | None = None, html_body: str | None = None) -> str:
        """Trả SENT (đã gửi email thật) hoặc SIMULATED."""
        if n.channel == "EMAIL" and email and self.smtp_enabled():
            self._smtp(email, subject or "SOA Cinema - Thông báo", body or n.message, html_body)
            logger.info("SENT email bookingId=%d to=%s", n.booking_id, mask_email(email))
            return SENT
        self.send(n)
        return SIMULATED

    @staticmethod
    def _smtp(to: str, subject: str, body: str, html_body: str | None = None) -> None:
        msg = EmailMessage()
        msg["From"] = config.SMTP_FROM or config.SMTP_USER
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")
        ctx = ssl.create_default_context()
        if config.SMTP_SSL:
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=config.SMTP_TIMEOUT, context=ctx)
        else:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=config.SMTP_TIMEOUT)
        with server:
            if not config.SMTP_SSL and config.SMTP_STARTTLS:
                server.starttls(context=ctx)
            if config.SMTP_USER:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)


def mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    return (name[:2] + "***@" + domain) if domain else "***"
