from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.core.config import settings, validate_runtime_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    register_error_handlers,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.routers.student_exam_runtime import router as student_exam_runtime_router
from app.routers.student_practice import router as student_practice_router
from app.routers.submissions import router as submissions_router
from app.routers.teacher_assignments import (
    router as teacher_assignments_router,
)
from app.routers.teacher_exams import (
    router as teacher_exams_router,
)
from app.routers.teacher_exams import (
    slot_generation_router,
)
from app.routers.teacher_groups import router as teacher_groups_router
from app.routers.teacher_results import router as teacher_results_router
from app.scheduler.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_runtime_settings(settings)
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
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


app.include_router(
    teacher_exams_router,
    prefix=settings.api_prefix,
)


app.include_router(
    slot_generation_router,
    prefix=settings.api_prefix,
)


app.include_router(
    teacher_results_router,
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


app.include_router(
    student_exam_runtime_router,
    prefix=settings.api_prefix,
)


app.include_router(
    student_practice_router,
    prefix=settings.api_prefix,
)


register_error_handlers(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "codeviva-api",
    }