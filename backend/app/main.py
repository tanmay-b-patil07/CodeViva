from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_error_handlers
from app.auth.router import router as auth_router
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from app.routers.submissions import router as submissions_router
from app.routers.teacher_groups import router as teacher_groups_router
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.routers.teacher_assignments import (
    router as teacher_assignments_router,
)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)


app.include_router(
    auth_router,
    prefix=settings.api_prefix,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    teacher_groups_router,
    prefix=settings.api_prefix,
)


app.include_router(
    teacher_assignments_router,
    prefix=settings.api_prefix,
)


app.add_exception_handler(
    AppError,
    app_error_handler,
)

app.add_exception_handler(
    HTTPException,
    http_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

app.add_exception_handler(
    Exception,
    unhandled_exception_handler,
)


app.include_router(
    submissions_router,
    prefix=settings.api_prefix,
)


register_error_handlers(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "codeviva-api",
    }