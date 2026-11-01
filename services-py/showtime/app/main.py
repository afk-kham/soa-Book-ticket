"""FastAPI application for the Showtime Service."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core import config


logger = logging.getLogger("showtime-service")


class NoContentPreflightCORSMiddleware(CORSMiddleware):
    def preflight_response(self, request_headers):
        response: Response = super().preflight_response(request_headers)
        if response.status_code == 200:
            response.status_code = 204
            response.body = b""
            response.headers["content-length"] = "0"
        return response


app = FastAPI(
    title="Showtime Service",
    version="1.0.0",
)
app.add_middleware(
    NoContentPreflightCORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(api_router)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _request: Request, _error: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "code": "VALIDATION_ERROR",
            "message": "Dữ liệu yêu cầu không hợp lệ",
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request, error: StarletteHTTPException
) -> JSONResponse:
    if error.status_code == 404:
        code, message = "NOT_FOUND", "Endpoint không tồn tại"
    elif error.status_code == 405:
        code, message = (
            "METHOD_NOT_ALLOWED",
            "Phương thức không được hỗ trợ trên endpoint này",
        )
    else:
        code, message = "HTTP_ERROR", "Yêu cầu không thể được xử lý"
    return JSONResponse(
        status_code=error.status_code,
        content={"status": "error", "code": code, "message": message},
        headers=error.headers,
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(
    _request: Request, error: Exception
) -> JSONResponse:
    logger.error(
        "Lỗi máy chủ nội bộ",
        exc_info=(type(error), error, error.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": "INTERNAL_ERROR",
            "message": "Lỗi máy chủ nội bộ",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT)
