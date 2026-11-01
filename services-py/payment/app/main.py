"""Entry point FastAPI của Payment Service (cổng 5005)."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core import config

MAX_BODY_BYTES = 1024 * 1024

app = FastAPI(
    title="Payment Service",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(api_router)


def cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "86400",
    }


@app.middleware("http")
async def body_and_cors_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return JSONResponse(status_code=204, content=None, headers=cors_headers())

    if request.method in {"POST", "PUT", "PATCH"}:
        body = await request.body()
        if len(body) > MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "status": "error",
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": "Nội dung yêu cầu vượt quá 1 MiB",
                },
                headers=cors_headers(),
            )

    content_length = request.headers.get("content-length")
    if request.method in {"POST", "PUT", "PATCH"} and content_length:
        try:
            if int(content_length) > MAX_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={
                        "status": "error",
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": "Nội dung yêu cầu vượt quá 1 MiB",
                    },
                    headers=cors_headers(),
                )
        except ValueError:
            pass

    try:
        response = await call_next(request)
    except Exception:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": "INTERNAL_ERROR",
                "message": "Lỗi máy chủ nội bộ",
            },
            headers=cors_headers(),
        )
    for key, value in cors_headers().items():
        response.headers[key] = value
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "code": "VALIDATION_ERROR",
            "message": "Dữ liệu yêu cầu không hợp lệ",
        },
        headers=cors_headers(),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    codes = {
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        422: "VALIDATION_ERROR",
    }
    messages = {
        404: "Không tìm thấy endpoint",
        405: "Phương thức không được hỗ trợ",
        422: "Dữ liệu yêu cầu không hợp lệ",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": codes.get(exc.status_code, "HTTP_ERROR"),
            "message": messages.get(exc.status_code, "Yêu cầu không hợp lệ"),
        },
        headers=cors_headers(),
    )


@app.exception_handler(Exception)
async def internal_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": "INTERNAL_ERROR",
            "message": "Lỗi máy chủ nội bộ",
        },
        headers=cors_headers(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT)
