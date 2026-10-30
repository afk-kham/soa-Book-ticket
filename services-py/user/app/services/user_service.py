"""Service: nghiệp vụ đăng ký / đăng nhập / tra cứu người dùng.

Không viết SQL, không biết HTTP. Chỉ gọi xuống Repository.
"""
import bcrypt

from app.entities import User, UserAccount
from app.repositories import DuplicateUsernameError, UserRepository
from app.services.errors import InvalidCredentialsError, UsernameTakenError, UserNotFoundError

BCRYPT_ROUNDS = 10  # cost 10, tiền tố $2a$ - khớp hash trong seed cũ
DEMO_TOKEN_PREFIX = "demo-token-"  # giữa kỳ (D-18 chưa chốt JWT)

_dummy_hash: bytes | None = None


def _get_dummy_hash() -> bytes:
    """Hash giả để đăng nhập tài khoản không tồn tại tốn thời gian tương đương (chống dò username)."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt(rounds=BCRYPT_ROUNDS, prefix=b"2a"))
    return _dummy_hash


def hash_password(password: str) -> str:
    """BCrypt ($2a$, cost 10). ``password`` đã được schema giới hạn <= 72 byte."""
    raw = password.encode("utf-8")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=BCRYPT_ROUNDS, prefix=b"2a")).decode("ascii")


def verify_password(password: str, password_hash: bytes | str) -> bool:
    """So khớp BCrypt; hash hỏng hoặc mật khẩu > 72 byte coi như không khớp (không ném lỗi)."""
    hashed = password_hash.encode("utf-8") if isinstance(password_hash, str) else password_hash
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed)
    except ValueError:
        return False


class UserService:
    def __init__(self, repository: UserRepository):
        self._repo = repository

    def register(self, username: str, password: str, email: str | None) -> User:
        """Đăng ký tài khoản mới. Role luôn là USER (không nhận role từ client)."""
        if self._repo.find_by_username(username) is not None:
            raise UsernameTakenError(username)
        password_hash = hash_password(password)
        try:
            return self._repo.insert(username, password_hash, email)
        except DuplicateUsernameError as exc:  # hai yêu cầu đồng thời cùng username
            raise UsernameTakenError(username) from exc

    def login(self, username: str, password: str) -> tuple[User, str]:
        """Kiểm tra BCrypt. Trả về (user công khai, token). Sai user và sai mật khẩu: CÙNG một lỗi."""
        account: UserAccount | None = self._repo.find_account_by_username(username)
        if account is None:
            verify_password(password, _get_dummy_hash())  # cân bằng thời gian xử lý
            raise InvalidCredentialsError()
        if not verify_password(password, account.password_hash):
            raise InvalidCredentialsError()
        return account.to_user(), self._issue_token(account)

    def list_users(self, username: str | None = None) -> list[User]:
        """Danh sách người dùng; có ``username`` thì trả mảng 0 hoặc 1 phần tử."""
        if username is None:
            return self._repo.find_all()
        user = self._repo.find_by_username(username)
        return [user] if user else []

    def get_user(self, user_id: int) -> User:
        user = self._repo.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    @staticmethod
    def _issue_token(account: UserAccount) -> str:
        # Giữa kỳ: token demo theo hợp đồng. Cuối kỳ (D-18) thay bằng JWT HS256 - xem README.
        return f"{DEMO_TOKEN_PREFIX}{account.username}"
