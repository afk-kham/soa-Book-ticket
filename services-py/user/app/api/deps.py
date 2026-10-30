"""Lắp ráp phụ thuộc: Repository -> Service -> Controller (mỗi request một bộ, không giữ kết nối)."""
from app.controllers import UserController
from app.repositories import UserRepository
from app.services import UserService


def get_user_controller() -> UserController:
    return UserController(UserService(UserRepository()))
