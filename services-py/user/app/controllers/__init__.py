"""Controller: nhận request từ router, gọi Service, dựng response theo hợp đồng."""
from app.controllers.user_controller import UserController

__all__ = ["UserController"]
