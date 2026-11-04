"""Router của Notification Service: khai báo path/method/mã HTTP và nối controller.

Sai method trả 405 (kèm header Allow) qua exception handler trong app/main.py.
"""
from fastapi import APIRouter

from app.controllers import notification_controller as c
from app.core import config
from app.schemas.notification import CreateLogRequest, NotifyRequest, UpdateLogRequest

api_router = APIRouter()


@api_router.get("/health")
def health():
    return {"status": "success", "data": {"service": config.SERVICE_NAME, "port": config.PORT}}


def _body(model):
    """Mô tả request body cho Swagger UI (body được đọc thủ công trong controller để giữ đúng mã lỗi/envelope)."""
    return {"requestBody": {"required": True, "content": {"application/json": {"schema": model.model_json_schema(by_alias=True)}}}}


R = api_router.add_api_route
R("/api/notify", c.notify, methods=["POST"], summary="Gửi thông báo giả lập + ghi log",
  openapi_extra=_body(NotifyRequest))
R("/api/notify/logs", c.list_logs, methods=["GET"], summary="Danh sách nhật ký (mới nhất trước)")
R("/api/notify/logs", c.create_log, methods=["POST"], status_code=201, summary="Tạo bản ghi nhật ký",
  openapi_extra=_body(CreateLogRequest))
# Phải khai báo TRƯỚC /logs/{log_id}: route khớp theo thứ tự, nếu sau thì "find" bị hiểu là log_id (400)
R("/api/notify/logs/find", c.find_key_word, methods=["GET"], summary="Tìm kiếm theo từ khóa trong nội dung")
R("/api/notify/logs/{log_id}", c.get_log, methods=["GET"], summary="Chi tiết một bản ghi")
R("/api/notify/logs/{log_id}", c.update_log, methods=["PUT"], summary="Cập nhật bản ghi (mọi trường tùy chọn)",
  openapi_extra=_body(UpdateLogRequest))
# PATCH cùng hành vi với PUT (hợp đồng §7 ghi PUT|PATCH): vẫn hoạt động nhưng ẩn khỏi Swagger cho đỡ rối
R("/api/notify/logs/{log_id}", c.update_log, methods=["PATCH"], include_in_schema=False)
R("/api/notify/logs/{log_id}", c.delete_log, methods=["DELETE"], summary="Xóa bản ghi")
