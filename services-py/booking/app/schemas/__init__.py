"""Schema: model Pydantic cho request/response của API (camelCase theo API_CONTRACT)."""
from app.schemas.booking import (
    BookingResponse,
    BookingResultResponse,
    CancelBookingRequest,
    CreateBookingRequest,
    OtpBookingRequest,
    OtpResponse,
    PayBookingRequest,
    UpdateBookingRequest,
)

__all__ = [
    "BookingResponse",
    "BookingResultResponse",
    "CancelBookingRequest",
    "CreateBookingRequest",
    "OtpBookingRequest",
    "OtpResponse",
    "PayBookingRequest",
    "UpdateBookingRequest",
]
