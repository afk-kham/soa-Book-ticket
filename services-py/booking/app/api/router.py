"""Router của Booking Service: chỉ khai báo path/method/mã HTTP và nối sang Controller.

Đặt/trả/hủy là hành động nên dùng POST. PUT chỉ đổi ghế của đơn đang giữ, DELETE xóa hẳn đơn.
Body được Controller tự đọc để giữ đúng thông báo lỗi của hợp đồng, nên phải khai báo tay cho Swagger.
"""
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.api.deps import get_booking_controller
from app.controllers import BookingController
from app.schemas import CancelBookingRequest, CreateBookingRequest, PayBookingRequest, UpdateBookingRequest

api_router = APIRouter()


def _body(model: type[BaseModel]) -> dict:
    schema = model.model_json_schema(by_alias=True)
    return {"requestBody": {"required": True, "content": {"application/json": {"schema": schema}}}}


@api_router.get("/health", tags=["health"], summary="Kiểm tra sống, có ping CSDL")
def health(controller: BookingController = Depends(get_booking_controller)):
    return controller.health()


@api_router.post(
    "/api/booking",
    status_code=201,
    tags=["booking"],
    summary="Đặt vé (điều phối). payNow=false: chỉ giữ ghế",
    openapi_extra=_body(CreateBookingRequest),
)
async def create_booking(request: Request, controller: BookingController = Depends(get_booking_controller)):
    return await controller.create(request)


@api_router.get("/api/booking", tags=["booking"], summary="Danh sách đơn")
async def list_bookings(
    request: Request,
    username: str | None = Query(default=None),
    status: str | None = Query(default=None, description="PENDING, PAID hoặc CANCELLED"),
    showtime_id: str | None = Query(default=None, alias="showtimeId"),
    controller: BookingController = Depends(get_booking_controller),
):
    return controller.list_bookings(request, username, status, showtime_id)


@api_router.get("/api/booking/seats", tags=["booking"], summary="Ghế đang giữ của một suất")
async def taken_seats(
    showtime_id: str | None = Query(default=None, alias="showtimeId"),
    controller: BookingController = Depends(get_booking_controller),
):
    return controller.seats(showtime_id)


@api_router.get("/api/booking/availability", tags=["booking"], summary="Số ghế đã giữ của nhiều suất")
async def availability(
    showtime_ids: str | None = Query(default=None, alias="showtimeIds", description="Ví dụ 1,2,3 (tối đa 500)"),
    controller: BookingController = Depends(get_booking_controller),
):
    return controller.availability(showtime_ids)


@api_router.get("/api/booking/{booking_id:int}", tags=["booking"], summary="Chi tiết đơn")
async def get_booking(
    request: Request, booking_id: int, controller: BookingController = Depends(get_booking_controller)
):
    return controller.get(request, booking_id)


@api_router.put(
    "/api/booking/{booking_id:int}",
    tags=["booking"],
    summary="Đổi ghế của đơn đang giữ ghế (PENDING)",
    openapi_extra=_body(UpdateBookingRequest),
)
async def update_booking(
    request: Request, booking_id: int, controller: BookingController = Depends(get_booking_controller)
):
    return await controller.update(request, booking_id)


@api_router.delete("/api/booking/{booking_id:int}", tags=["booking"], summary="Xóa hẳn đơn (chủ đơn hoặc ADMIN)")
async def delete_booking(
    request: Request,
    booking_id: int,
    username: str | None = Query(default=None, description="Bỏ qua khi bật JWT_REQUIRED: lấy từ token"),
    controller: BookingController = Depends(get_booking_controller),
):
    return controller.delete(request, booking_id, username)


@api_router.post(
    "/api/booking/{booking_id:int}/pay",
    tags=["booking"],
    summary="Thanh toán đơn đang giữ ghế; thất bại thì đơn vẫn PENDING",
    openapi_extra=_body(PayBookingRequest),
)
async def pay_booking(
    request: Request, booking_id: int, controller: BookingController = Depends(get_booking_controller)
):
    return await controller.pay(request, booking_id)


@api_router.post(
    "/api/booking/{booking_id:int}/cancel",
    tags=["booking"],
    summary="Hủy đơn đang giữ ghế (nhả ghế)",
    openapi_extra=_body(CancelBookingRequest),
)
async def cancel_booking(
    request: Request, booking_id: int, controller: BookingController = Depends(get_booking_controller)
):
    return await controller.cancel(request, booking_id)
