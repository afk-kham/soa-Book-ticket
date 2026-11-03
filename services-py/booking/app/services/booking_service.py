"""Nghiệp vụ Booking: ORCHESTRATOR của luồng đặt vé (thay Program.cs).

User -> Movie -> Showtime -> giữ ghế (PENDING) -> Payment -> PAID/CANCELLED -> Notification.
Không biết mã HTTP trả cho client (chỉ ném BookingError), không viết SQL.

Đồng thời: SQL chạy tuần tự trên event loop, còn "kiểm tra ghế + lưu đơn" nằm trong một giao dịch
BEGIN IMMEDIATE nên hai yêu cầu cùng giành một ghế chỉ có đúng một yêu cầu thắng (D-10).
Không có giao dịch phân tán: dùng trạng thái + bù trừ kiểu Saga đơn giản (INTEGRATION_FLOW.md §3).
"""
import logging
from datetime import datetime, timedelta

from app.core import clock, config
from app.core.errors import BookingError, validation_error
from app.entities import (
    CANCELLED,
    MAX_ID,
    NOTIFICATION_FAILED,
    NOTIFICATION_SENT,
    NOTIFICATION_SKIPPED,
    PAID,
    PAYMENT_FAILED,
    PAYMENT_PAID,
    PENDING,
    Booking,
    BookingResult,
    PaymentOutcome,
)
from app.repositories import BookingRepository
from app.services.upstream import Reply, UpstreamClient

logger = logging.getLogger("booking-service")

NOTIFICATION_TIMEOUT_SECONDS = 3
RECONCILE_TIMEOUT_SECONDS = 2


def _starts_at(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=None)
    except ValueError:
        return None


def _outcome(transaction: dict, method: str) -> PaymentOutcome:
    """Giao dịch Payment -> kết quả thanh toán. id vẫn đọc được nếu Payment đổi kiểu số/chuỗi (D-04)."""
    transaction_id = transaction.get("id")
    return PaymentOutcome(
        status=str(transaction.get("status") or PAYMENT_FAILED),
        method=method,
        transaction_id=None if transaction_id is None else str(transaction_id),
    )


class BookingService:
    def __init__(self, repository: BookingRepository, upstream: UpstreamClient):
        self._repo = repository
        self._upstream = upstream

    def ping(self) -> None:
        self._repo.ping()

    def expire_holds(self) -> int:
        """Hủy các đơn PENDING quá HOLD_MINUTES phút (nhả ghế). Trả về số đơn bị hủy."""
        return self._expire_holds(self._repo)

    @staticmethod
    def _expire_holds(repo: BookingRepository) -> int:
        cutoff = clock.now() - timedelta(minutes=config.HOLD_MINUTES)
        expired = repo.expire_pending(clock.format_time(cutoff))
        if expired:
            logger.info("%d đơn hết hạn giữ ghế -> CANCELLED", expired)
        return expired

    # ------------------------------------------------------------------ đặt vé
    async def create_booking(
        self,
        username: str,
        movie_id: int,
        showtime_id: int,
        seats: list[str],
        method: str,
        pay_now: bool,
        authorization: str | None = None,
    ) -> BookingResult:
        # 1) Xác thực tham chiếu logic bằng API của các service sở hữu dữ liệu
        await self._ensure_user_exists(username)
        await self._ensure_movie_exists(movie_id)
        price = await self._showtime_price(showtime_id, movie_id)

        # 2) Giữ ghế: lưu đơn PENDING. Giá lấy từ Showtime, không tin client
        pending = self._hold_seats(movie_id, showtime_id, username, seats, price * len(seats))
        if not pay_now:  # chỉ giữ ghế: chưa gọi Payment
            return BookingResult(pending, None, NOTIFICATION_SKIPPED)

        # 3) Thanh toán (lỗi -> hủy đơn, nhả ghế)
        payment = await self._charge_or_cancel(pending, method, authorization)
        final_status = PAID if payment.status == PAYMENT_PAID else CANCELLED
        self._repo.update_status(pending.id, final_status)

        # 4) Thông báo (best-effort): Notification lỗi KHÔNG làm hỏng đơn đã PAID
        notification = await self._notify(username, pending.id) if final_status == PAID else NOTIFICATION_SKIPPED
        return BookingResult(self._find(pending.id), payment, notification)

    async def _ensure_user_exists(self, username: str) -> None:
        reply = await self._upstream.send(
            "GET",
            f"{config.USER_SERVICE_URL.rstrip('/')}/api/users",
            "User Service",
            "USER_SERVICE_UNAVAILABLE",
            params={"username": username},
        )
        if not reply.ok:
            raise BookingError("USER_SERVICE_ERROR", "User Service trả lỗi khi kiểm tra người dùng")
        if not isinstance(reply.data, list) or not reply.data:
            raise BookingError("USER_NOT_FOUND", f"Không tồn tại người dùng '{username}'")

    async def _ensure_movie_exists(self, movie_id: int) -> None:
        reply = await self._upstream.send(
            "GET",
            f"{config.MOVIE_SERVICE_URL.rstrip('/')}/api/movies/{movie_id}",
            "Movie Service",
            "MOVIE_SERVICE_UNAVAILABLE",
        )
        if reply.status == 404:
            raise BookingError("MOVIE_NOT_FOUND", f"Không tồn tại phim movieId = {movie_id}")
        if not reply.ok:
            raise BookingError("MOVIE_SERVICE_ERROR", "Movie Service trả lỗi khi kiểm tra phim")

    async def _showtime_price(self, showtime_id: int, movie_id: int) -> int:
        """Kiểm tra suất chiếu còn đặt được và trả giá một ghế."""
        reply = await self._upstream.send(
            "GET",
            f"{config.SHOWTIME_SERVICE_URL.rstrip('/')}/api/showtimes/{showtime_id}",
            "Showtime Service",
            "SHOWTIME_SERVICE_UNAVAILABLE",
        )
        if reply.status == 404:
            raise BookingError("SHOWTIME_NOT_FOUND", f"Không tồn tại suất chiếu showtimeId = {showtime_id}")
        showtime = reply.data if reply.ok and isinstance(reply.data, dict) else {}
        price = showtime.get("price")
        if not isinstance(price, int) or not isinstance(showtime.get("movieId"), int):
            raise BookingError("SHOWTIME_SERVICE_ERROR", "Showtime Service trả lỗi khi kiểm tra suất chiếu")
        if showtime["movieId"] != movie_id:
            raise validation_error("Suất chiếu không thuộc phim đã chọn (movieId không khớp)")
        starts_at = _starts_at(showtime.get("time"))
        if starts_at is not None and starts_at <= clock.now():
            raise BookingError("SHOWTIME_CLOSED", "Suất chiếu đã bắt đầu, vui lòng chọn suất khác")
        return price

    def _hold_seats(
        self, movie_id: int, showtime_id: int, username: str, seats: list[str], total_price: int
    ) -> Booking:
        with self._repo.transaction() as tx:
            self._expire_holds(tx)  # nhả ghế của đơn quá hạn trước khi kiểm tra
            taken = tx.taken_seats(showtime_id)
            clash = [seat for seat in seats if seat in taken]
            if clash:
                raise BookingError("SEAT_TAKEN", f"Ghế đã có người đặt: {', '.join(clash)}")
            return tx.insert_pending(
                movie_id, showtime_id, username, seats, total_price, clock.format_time(clock.now())
            )

    async def _charge_or_cancel(self, booking: Booking, method: str, authorization: str | None) -> PaymentOutcome:
        """Luồng đặt-và-trả-ngay: Payment lỗi hoặc không với tới được -> hủy đơn (nhả ghế) rồi báo lỗi."""
        try:
            return await self._charge(booking, method, authorization)
        except BookingError as exc:
            self._repo.update_status(booking.id, CANCELLED)
            raise BookingError(exc.code, f"{exc.message}. Đơn #{booking.id} đã bị hủy, ghế được nhả lại") from exc

    # ------------------------------------------------------------------ thanh toán sau
    async def pay_booking(
        self,
        booking_id: int,
        username: str,
        method: str,
        is_admin: bool = False,
        authorization: str | None = None,
    ) -> BookingResult:
        """Thanh toán đơn đang giữ ghế. Khác đặt-và-trả-ngay: thanh toán thất bại hoặc Payment tạm sập
        thì đơn VẪN PENDING để người dùng thử lại / đổi phương thức cho tới khi hết hạn giữ ghế."""
        self.expire_holds()
        booking = self._owned(booking_id, username, is_admin)
        if booking.status == PAID:
            raise BookingError("ALREADY_PAID", f"Đơn #{booking_id} đã được thanh toán")
        if booking.status == CANCELLED:
            raise BookingError("BOOKING_CANCELLED", f"Đơn #{booking_id} đã hết hạn giữ ghế hoặc đã bị hủy")

        payment = await self._charge(booking, method, authorization)
        notification = NOTIFICATION_SKIPPED
        if payment.status == PAYMENT_PAID and self._settle_paid(booking):
            notification = await self._notify(booking.username, booking_id)
        return BookingResult(self._find(booking_id), payment, notification)

    def _settle_paid(self, booking: Booking) -> bool:
        """Chốt PAID sau khi Payment đã nhận tiền. Trả True nếu chính lần gọi này chốt được đơn."""
        if self._repo.try_update_status(booking.id, PENDING, PAID):
            return True
        # Đơn vừa rời PENDING trong lúc chờ Payment: bị quét hết hạn, hoặc yêu cầu song song đã chốt trước
        with self._repo.transaction() as tx:
            if self._find(booking.id, tx).status == PAID:
                return False
            if tx.taken_seats(booking.showtime_id) & set(booking.seats):
                logger.error(
                    "Đơn #%d thanh toán sau khi hết hạn và ghế đã bị lấy - cần hoàn tiền thủ công", booking.id
                )
                return False
            tx.update_status(booking.id, PAID)  # tiền đã nhận và ghế chưa ai lấy: chốt PAID
            return True

    # ------------------------------------------------------------------ hủy
    def cancel_booking(self, booking_id: int, username: str, is_admin: bool = False) -> BookingResult:
        self.expire_holds()
        booking = self._owned(booking_id, username, is_admin)
        if booking.status == PAID:
            raise BookingError(
                "PAID_NOT_CANCELLABLE", "Vé đã thanh toán không thể hủy trực tuyến, vui lòng liên hệ quầy vé"
            )
        if booking.status == PENDING:
            self._repo.try_update_status(booking_id, PENDING, CANCELLED)
        return BookingResult(self._find(booking_id), None, NOTIFICATION_SKIPPED)

    # ------------------------------------------------------------------ đọc
    def list_bookings(self, username: str | None, status: str | None, showtime_id: int | None) -> list[Booking]:
        self.expire_holds()
        return self._repo.find_all(username, status, showtime_id)

    def get_booking(self, booking_id: int, viewer: str | None = None, is_admin: bool = False) -> Booking:
        """Chi tiết đơn. Có ``viewer`` (đã bật JWT) thì chỉ chủ đơn hoặc ADMIN được xem."""
        self.expire_holds()
        if viewer is None:
            return self._find(booking_id)
        return self._owned(booking_id, viewer, is_admin)

    def taken_seats(self, showtime_id: int) -> list[str]:
        self.expire_holds()
        return sorted(self._repo.taken_seats(showtime_id))

    def availability(self, showtime_ids: list[int]) -> dict[int, int]:
        self.expire_holds()
        return self._repo.taken_counts(showtime_ids)

    def _find(self, booking_id: int, repo: BookingRepository | None = None) -> Booking:
        booking = (repo or self._repo).get(booking_id) if booking_id <= MAX_ID else None
        if booking is None:
            raise BookingError("NOT_FOUND", f"Không tìm thấy đơn đặt vé có id {booking_id}")
        return booking

    def _owned(self, booking_id: int, username: str, is_admin: bool) -> Booking:
        booking = self._find(booking_id)
        if not is_admin and booking.username != username:
            raise BookingError("FORBIDDEN", "Bạn không có quyền thao tác với đơn này")
        return booking

    # ------------------------------------------------------------------ gọi Payment / Notification
    async def _charge(self, booking: Booking, method: str, authorization: str | None) -> PaymentOutcome:
        """Gọi Payment, trả kết quả PAID|FAILED. Không đổi trạng thái đơn; lỗi -> BookingError."""
        # Chuyển tiếp nguyên token: Starlette giải mã header bằng latin-1 nên encode lại không làm đổi byte
        headers = {"Authorization": authorization.encode("latin-1")} if authorization else None
        try:
            reply = await self._upstream.send(
                "POST",
                f"{config.PAYMENT_SERVICE_URL.rstrip('/')}/api/payment",
                "Payment Service",
                "PAYMENT_SERVICE_UNAVAILABLE",
                json={"bookingId": booking.id, "amount": booking.total_price, "method": method},
                headers=headers,
            )
        except BookingError:
            # Có thể Payment đã ghi giao dịch nhưng phản hồi bị mất: hỏi lại trước khi kết luận
            known = await self._reconcile(booking.id, method, headers)
            if known is not None:
                return known
            raise
        if reply.ok and isinstance(reply.data, dict) and "status" in reply.data:
            return _outcome(reply.data, method)
        if reply.status == 409:  # ALREADY_PAID: đơn đã trả trước đó
            known = await self._reconcile(booking.id, method, headers)
            if known is not None and known.status == PAYMENT_PAID:
                return known
        raise BookingError("PAYMENT_SERVICE_ERROR", f"Payment Service từ chối giao dịch ({self._reason(reply)})")

    @staticmethod
    def _reason(reply: Reply) -> str:
        return reply.message or f"HTTP {reply.status}"

    async def _reconcile(self, booking_id: int, method: str, headers: dict | None) -> PaymentOutcome | None:
        """Giao dịch đã ghi nhận của đơn: ưu tiên giao dịch PAID, không có thì lấy giao dịch mới nhất."""
        try:
            reply = await self._upstream.send(
                "GET",
                f"{config.PAYMENT_SERVICE_URL.rstrip('/')}/api/payment",
                "Payment Service",
                "PAYMENT_SERVICE_UNAVAILABLE",
                params={"bookingId": booking_id},
                headers=headers,
                timeout=RECONCILE_TIMEOUT_SECONDS,
            )
        except BookingError:
            return None
        if not reply.ok or not isinstance(reply.data, list) or not reply.data:
            return None
        paid = (tx for tx in reply.data if isinstance(tx, dict) and tx.get("status") == PAYMENT_PAID)
        transaction = next(paid, reply.data[0])
        return _outcome(transaction, method) if isinstance(transaction, dict) else None

    async def _notify(self, username: str, booking_id: int) -> str:
        """Gửi thông báo xác nhận (best-effort) -> SENT | FAILED."""
        headers = {"X-Internal-Key": config.INTERNAL_KEY} if config.INTERNAL_KEY else None
        try:
            reply = await self._upstream.send(
                "POST",
                f"{config.NOTIFICATION_SERVICE_URL.rstrip('/')}/api/notify",
                "Notification Service",
                "NOTIFICATION_SERVICE_UNAVAILABLE",
                json={"username": username, "bookingId": booking_id, "channel": "EMAIL"},
                headers=headers,
                timeout=NOTIFICATION_TIMEOUT_SECONDS,
            )
        except BookingError:
            reply = None
        if reply is not None and reply.ok:
            return NOTIFICATION_SENT
        logger.warning("Không gửi được thông báo cho đơn #%d (đơn vẫn PAID)", booking_id)
        return NOTIFICATION_FAILED
