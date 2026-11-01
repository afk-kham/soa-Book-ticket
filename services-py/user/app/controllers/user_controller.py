"""Controller: nhận dữ liệu từ Router, gọi Service, dựng envelope + mã HTTP. Không viết SQL."""
import re

from app.core.http import EnvelopeResponse, error, success
from app.schemas import LoginRequest, LoginResponse, RegisterRequest, UserResponse
from app.services import InvalidCredentialsError, UsernameTakenError, UserNotFoundError, UserService

_ID_RE = re.compile(r"[+-]?[0-9]+")  # chỉ chữ số ASCII
_INT32_MAX = 2_147_483_647  # id cũ là INT (Java Integer.parseInt)


class UserController:
    def __init__(self, service: UserService):
        self._service = service

    def register(self, body: RegisterRequest) -> EnvelopeResponse:
        try:
            user = self._service.register(body.username, body.password, body.email)
        except UsernameTakenError:
            return error(409, "Tên đăng nhập đã tồn tại", code="CONFLICT")
        return success(201, UserResponse.from_entity(user).model_dump(by_alias=True))

    def login(self, body: LoginRequest) -> EnvelopeResponse:
        try:
            user, token = self._service.login(body.username, body.password)
        except InvalidCredentialsError:
            return error(401, "Sai tên đăng nhập hoặc mật khẩu", code="UNAUTHORIZED")
        data = LoginResponse(id=user.id, username=user.username, role=user.role, token=token)
        return success(200, data.model_dump(by_alias=True))

    def list_users(self, username: str | None) -> EnvelopeResponse:
        users = self._service.list_users(username.strip() if username is not None else None)
        return success(200, [UserResponse.from_entity(u).model_dump(by_alias=True) for u in users])

    def get_user(self, raw_id: str) -> EnvelopeResponse:
        if not _ID_RE.fullmatch(raw_id):
            return error(400, "id phải là số nguyên", code="VALIDATION_ERROR")
        user_id = int(raw_id)
        if user_id <= 0 or user_id > _INT32_MAX:
            return error(400, "id phải là số nguyên dương", code="VALIDATION_ERROR")
        try:
            user = self._service.get_user(user_id)
        except UserNotFoundError:
            return error(404, f"Không tìm thấy người dùng có id {user_id}", code="NOT_FOUND")
        return success(200, UserResponse.from_entity(user).model_dump(by_alias=True))
