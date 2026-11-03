"""Lắp ráp phụ thuộc: Repository -> Service -> Controller (mỗi request một bộ, không giữ kết nối)."""
from fastapi import Depends

from app.controllers import BookingController
from app.repositories import BookingRepository
from app.services import BookingService, UpstreamClient

upstream = UpstreamClient()


def get_upstream() -> UpstreamClient:
    return upstream


def get_booking_controller(client: UpstreamClient = Depends(get_upstream)) -> BookingController:
    return BookingController(BookingService(BookingRepository(), client))
