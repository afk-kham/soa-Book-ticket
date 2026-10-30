"""Router của User Service: chỉ khai báo path/method/mã HTTP và nối sang Controller.

Chỉ các endpoint có trong API_CONTRACT §4 + /health (hạ tầng). KHÔNG có PUT/PATCH/DELETE.
"""
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_user_controller
from app.controllers import UserController
from app.core import config
from app.schemas import LoginRequest, RegisterRequest

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
def health():
    return {"status": "success", "data": {"service": config.SERVICE_NAME, "port": config.PORT}}


@api_router.post("/api/register", status_code=201, tags=["users"], summary="Đăng ký (role luôn USER)")
def register(body: RegisterRequest, controller: UserController = Depends(get_user_controller)):
    return controller.register(body)


@api_router.post("/api/login", status_code=200, tags=["users"], summary="Đăng nhập (BCrypt)")
def login(body: LoginRequest, controller: UserController = Depends(get_user_controller)):
    return controller.login(body)


@api_router.get("/api/users", tags=["users"], summary="Danh sách; ?username=x -> mảng 0/1 phần tử")
def list_users(
    username: str | None = Query(default=None),
    controller: UserController = Depends(get_user_controller),
):
    return controller.list_users(username)


@api_router.get("/api/users/{user_id}", tags=["users"], summary="Chi tiết theo id")
def get_user(user_id: str, controller: UserController = Depends(get_user_controller)):
    return controller.get_user(user_id)
