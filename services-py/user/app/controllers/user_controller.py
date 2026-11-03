"""Controller: nhận dữ liệu từ Router, gọi Service, dựng envelope + mã HTTP. Không viết SQL."""
import re

from app.core.http import EnvelopeResponse, error, success
from app.schemas import (
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UpdateUserRequest,
    UserResponse,
)
from app.services import (
    InvalidCredentialsError,
    LastAdminError,
    UsernameTakenError,
    UserNotFoundError,
    UserService,
)

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
        user_id, bad = _parse_id(raw_id)
        if bad:
            return bad
        try:
            user = self._service.get_user(user_id)
        except UserNotFoundError:
            return _not_found(user_id)
        return success(200, UserResponse.from_entity(user).model_dump(by_alias=True))

    def create_user(self, body: CreateUserRequest) -> EnvelopeResponse:
        try:
            user = self._service.create_user(body.username, body.password, body.email, body.role)
        except UsernameTakenError:
            return error(409, "Tên đăng nhập đã tồn tại", code="CONFLICT")
        return success(201, UserResponse.from_entity(user).model_dump(by_alias=True))

    def update_user(self, raw_id: str, body: UpdateUserRequest) -> EnvelopeResponse:
        user_id, bad = _parse_id(raw_id)
        if bad:
            return bad
        try:
            user = self._service.update_user(user_id, body.changes())
        except UserNotFoundError:
            return _not_found(user_id)
        except UsernameTakenError:
            return error(409, "Tên đăng nhập đã tồn tại", code="CONFLICT")
        except LastAdminError:
            return error(409, "Không thể hạ quyền quản trị viên cuối cùng", code="CONFLICT")
        return success(200, UserResponse.from_entity(user).model_dump(by_alias=True))

    def delete_user(self, raw_id: str) -> EnvelopeResponse:
        user_id, bad = _parse_id(raw_id)
        if bad:
            return bad
        try:
            self._service.delete_user(user_id)
        except UserNotFoundError:
            return _not_found(user_id)
        except LastAdminError:
            return error(409, "Không thể xóa quản trị viên cuối cùng", code="CONFLICT")
        return success(200, {"id": user_id, "deleted": True})


def _parse_id(raw_id: str) -> tuple[int, EnvelopeResponse | None]:
    if not _ID_RE.fullmatch(raw_id):
        return 0, error(400, "id phải là số nguyên", code="VALIDATION_ERROR")
    user_id = int(raw_id)
    if user_id <= 0 or user_id > _INT32_MAX:
        return 0, error(400, "id phải là số nguyên dương", code="VALIDATION_ERROR")
    return user_id, None


def _not_found(user_id: int) -> EnvelopeResponse:
    return error(404, f"Không tìm thấy người dùng có id {user_id}", code="NOT_FOUND")
