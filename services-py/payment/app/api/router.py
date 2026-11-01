"""Router của Payment Service."""
import re

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from app.core import config
from app.controllers import get_payments_controller, post_payment
from app.schemas import PaymentCreateRequest

api_router = APIRouter()


@api_router.get("/health")
def health():
    return {"status": "success", "data": {"service": config.SERVICE_NAME, "port": config.PORT}}


@api_router.post("/api/payment", status_code=201)
def create_payment(payload: PaymentCreateRequest = Body(...)):
    return post_payment(payload)


@api_router.get("/api/payment", status_code=200)
def list_payments(bookingId: str | None = Query(default=None, alias="bookingId")):
    if bookingId is None:
        return get_payments_controller()
    if (
        not re.fullmatch(r"[0-9]+", bookingId)
        or int(bookingId) <= 0
        or int(bookingId) > 9223372036854775807
    ):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": "VALIDATION_ERROR",
                "message": "bookingId phải là số nguyên dương",
            },
        )
    return get_payments_controller(int(bookingId))
