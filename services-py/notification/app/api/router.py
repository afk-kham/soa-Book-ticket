"""Router của Notification Service: khai báo path/method/mã HTTP và nối controller.

Sai method trả 405 (kèm header Allow) qua exception handler trong app/main.py.
"""
from fastapi import APIRouter

from app.controllers import notification_controller as c
from app.core import config
from app.schemas.notification import CreateLogRequest, NotifyRequest, UpdateLogRequest

api_router = APIRouter()


api_router.add_api_route("/", c.list_all, methods=["GET"], summary="Trang gốc: toàn bộ nhật ký hiện có trong CSDL")


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
R("/api/notify/logs/{log_id}", c.get_log, methods=["GET"], summary="Chi tiết một bản ghi")
for _m in ("PUT", "PATCH"):
    R("/api/notify/logs/{log_id}", c.update_log, methods=[_m], operation_id=f"update_log_{_m.lower()}",
      summary="Cập nhật bản ghi (mọi trường tùy chọn)", openapi_extra=_body(UpdateLogRequest))
R("/api/notify/logs/{log_id}", c.delete_log, methods=["DELETE"], summary="Xóa bản ghi")
