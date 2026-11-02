"""Gọi service khác bằng HTTP + JSON (thay Upstream.cs).

Đây là CÁCH DUY NHẤT Booking lấy dữ liệu của User/Movie/Showtime/Payment/Notification:
Booking không đọc CSDL của họ, không import code của họ.
"""
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.core import config
from app.core.errors import BookingError

logger = logging.getLogger("booking-service")


@dataclass(frozen=True)
class Reply:
    """Phản hồi của service khác, đã giải mã envelope {"status","data"|"message"}."""

    status: int
    data: Any = None
    message: str | None = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


def _default_transport() -> httpx.AsyncHTTPTransport:
    # IPv4: "localhost" trên Windows ra ::1 trước trong khi các service chỉ nghe 0.0.0.0, mỗi lời gọi sẽ
    # trễ vô ích (thay ConnectIPv4FirstAsync). Không giữ kết nối: service kia đóng kết nối rảnh đúng lúc
    # đang gửi thì POST /api/payment sẽ báo lỗi giả.
    return httpx.AsyncHTTPTransport(local_address="0.0.0.0", limits=httpx.Limits(max_keepalive_connections=0))


class UpstreamClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._client = httpx.AsyncClient(transport=transport or _default_transport(), trust_env=False)

    async def send(
        self,
        method: str,
        url: str,
        service_name: str,
        unavailable_code: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: float | None = None,
    ) -> Reply:
        """Gửi request. Không kết nối được hoặc quá hạn -> BookingError(unavailable_code)."""
        try:
            response = await self._client.request(
                method,
                url,
                json=json,
                params=params,
                headers=headers,
                timeout=timeout or config.UPSTREAM_TIMEOUT_SECONDS,
            )
        except httpx.RequestError as exc:
            logger.warning("%s không phản hồi (%s): %s", service_name, url, type(exc).__name__)
            raise BookingError(unavailable_code, f"{service_name} đang không khả dụng, vui lòng thử lại sau") from exc
        try:
            body = response.json()
        except ValueError:  # không phải JSON: bỏ qua, chỉ dùng mã HTTP
            body = None
        if not isinstance(body, dict):
            return Reply(response.status_code)
        message = body.get("message")
        return Reply(response.status_code, body.get("data"), message if isinstance(message, str) else None)

    async def aclose(self) -> None:
        await self._client.aclose()
