"""Pydantic request/response (camelCase theo API_CONTRACT §7).

Request: trường lạ bị từ chối (extra=forbid); kiểu nghiêm ngặt để "1" hay 1.5 không lọt vào bookingId.
Trường vắng mặt nhận giá trị rỗng/0 để thông báo lỗi do service quyết định (giữ hành vi code cũ).
"""
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

from app.entities.notification_log import NotificationLog


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=False)


class NotifyRequest(_Request):
    username: StrictStr = ""
    booking_id: StrictInt = Field(0, alias="bookingId")
    channel: StrictStr = ""


class CreateLogRequest(_Request):
    username: StrictStr = ""
    recipient: StrictStr = ""
    booking_id: StrictInt = Field(0, alias="bookingId")
    channel: StrictStr = ""
    message: StrictStr = ""
    content: StrictStr = ""


class UpdateLogRequest(_Request):
    username: StrictStr | None = None
    recipient: StrictStr | None = None
    booking_id: StrictInt | None = Field(None, alias="bookingId")
    channel: StrictStr | None = None
    message: StrictStr | None = None
    content: StrictStr | None = None


def log_to_dict(n: NotificationLog) -> dict:
    return {"id": n.id, "bookingId": n.booking_id, "username": n.username,
            "channel": n.channel, "message": n.message, "sentAt": n.sent_at}


def notify_to_dict(n: NotificationLog) -> dict:
    return {"notificationId": n.id, "bookingId": n.booking_id, "username": n.username,
            "channel": n.channel, "deliveryStatus": "SIMULATED", "message": n.message, "sentAt": n.sent_at}
