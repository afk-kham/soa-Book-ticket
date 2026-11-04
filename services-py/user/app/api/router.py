"""Router của User Service: chỉ khai báo path/method/mã HTTP và nối sang Controller.

Chỉ các endpoint có trong API_CONTRACT §4 + /health (hạ tầng). /api/users có đủ CRUD (TV3 đã đồng ý).
"""
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_user_controller
from app.controllers import UserController
from app.core import config
from app.schemas import CreateUserRequest, LoginRequest, RegisterRequest, UpdateUserRequest

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



@api_router.post("/api/users", status_code=201, tags=["users"], summary="Admin tạo người dùng (role USER/ADMIN)")
def create_user(body: CreateUserRequest, controller: UserController = Depends(get_user_controller)):
    return controller.create_user(body)


@api_router.put("/api/users/{user_id}", tags=["users"], summary="Sửa người dùng (mọi trường tùy chọn)")
def update_user(user_id: str, body: UpdateUserRequest, controller: UserController = Depends(get_user_controller)):
    return controller.update_user(user_id, body)


# PATCH cùng hành vi với PUT: vẫn hoạt động nhưng ẩn khỏi Swagger cho gọn
@api_router.patch("/api/users/{user_id}", include_in_schema=False)
def patch_user(user_id: str, body: UpdateUserRequest, controller: UserController = Depends(get_user_controller)):
    return controller.update_user(user_id, body)


@api_router.delete("/api/users/{user_id}", tags=["users"], summary="Xóa người dùng (không xóa ADMIN cuối cùng)")
def delete_user(user_id: str, controller: UserController = Depends(get_user_controller)):
    return controller.delete_user(user_id)
