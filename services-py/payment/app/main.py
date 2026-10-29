"""Entry point FastAPI của Payment Service (cổng 5005).

Chạy local:  uvicorn app.main:app --host 0.0.0.0 --port 5005
TODO(nhóm trưởng): error envelope {"status":"error","code","message"} và OPTIONS->204 theo API_CONTRACT
(CORSMiddleware của Starlette trả 200 cho preflight) - xem docs/OPEN_QUESTIONS.md mục D-07.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core import config

app = FastAPI(title="Payment Service", version="0.0.1-scaffold")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT)
