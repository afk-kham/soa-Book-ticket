"""Router của Notification Service.

Hiện chỉ có /health (hạ tầng, dùng cho Docker healthcheck).
Dạng trả về khớp với health của Showtime/Booking/Payment hiện có (envelope + service + port).
TODO(TV6): thêm route nghiệp vụ theo API_CONTRACT.md (Router -> Controller -> Service -> Repository).
"""
from fastapi import APIRouter

from app.core import config

api_router = APIRouter()


@api_router.get("/health")
def health():
    return {"status": "success", "data": {"service": config.SERVICE_NAME, "port": config.PORT}}
