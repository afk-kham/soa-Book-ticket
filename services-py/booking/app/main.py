"""Entry point FastAPI của Booking Service (cổng 5004).

Chạy local:  python -m app.db.init_db --seed  rồi  uvicorn app.main:app --host 0.0.0.0 --port 5004
Swagger UI:  http://localhost:5004/docs

- Import module và khởi động KHÔNG tạo schema, KHÔNG nạp dữ liệu: đó là bước tường minh ở trên.
- CORS/OPTIONS->204/envelope lỗi: xem ``app/core/http.py`` (D-07, xử lý trong phạm vi service).
- Chỉ chạy MỘT tiến trình Uvicorn (D-03, D-10).
"""
import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.deps import upstream
from app.api.router import api_router
from app.controllers import handle_booking_error
from app.core import config
from app.core.errors import BookingError
from app.core.http import register_http_handling
from app.repositories import BookingRepository
from app.services import BookingService

logger = logging.getLogger("booking-service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SWEEP_INTERVAL_SECONDS = 30


async def _sweep_expired_holds() -> None:
    """Định kỳ hủy đơn PENDING quá hạn (ngoài ra các yêu cầu đọc/đặt cũng tự quét trước)."""
    service = BookingService(BookingRepository(), upstream)
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        try:
            service.expire_holds()
        except Exception as exc:  # noqa: BLE001 - vòng quét không được chết vì một lần lỗi
            logger.error("Quét đơn quá hạn lỗi: %s", type(exc).__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    sweeper = asyncio.create_task(_sweep_expired_holds())
    yield
    sweeper.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await sweeper
    await upstream.aclose()


app = FastAPI(title="Booking Service", version="1.0.0", lifespan=lifespan)
register_http_handling(app, api_router)
app.add_exception_handler(BookingError, handle_booking_error)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT)
