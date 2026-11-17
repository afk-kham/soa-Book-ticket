"""Truy vết request xuyên service: mã X-Request-ID + dòng nhật ký truy cập.

- Nhận X-Request-ID từ client/API Gateway (chỉ chấp nhận ký tự an toàn, tối đa 64), không có thì tự sinh.
- Trả lại header X-Request-ID cho phía gọi; Booking chuyển tiếp mã này khi gọi service khác, nên một lần đặt vé
  có cùng một mã trong log của cả 6 service (lọc log theo `rid=<mã>` là thấy toàn bộ hành trình).
- Chỉ ghi method, path, mã HTTP, thời gian xử lý: KHÔNG ghi body, query hay header (tránh lộ OTP/mật khẩu/token).
"""
import contextvars
import logging
import re
import time
import uuid

_SAFE_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

trace_log = logging.getLogger("trace")
if not trace_log.handlers:  # logger riêng, không phụ thuộc cấu hình logging của từng service
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    trace_log.addHandler(_handler)
    trace_log.setLevel(logging.INFO)
    trace_log.propagate = False


class RequestIdMiddleware:
    """ASGI thuần: độc lập với các middleware/exception handler sẵn có của service."""

    def __init__(self, app, service: str = "service"):
        self.app = app
        self.service = service

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = ""
        for name, value in scope["headers"]:
            if name == b"x-request-id":
                incoming = value.decode("latin-1")
                break
        rid = incoming if _SAFE_ID.fullmatch(incoming) else uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [*message.get("headers", []), (b"x-request-id", rid.encode("ascii"))]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            trace_log.info("rid=%s service=%s %s %s -> %s %.0fms", rid, self.service, scope["method"],
                           scope["path"], status, (time.perf_counter() - started) * 1000)
            request_id_var.reset(token)
