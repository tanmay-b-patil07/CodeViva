import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import HTTPException, Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


logger = logging.getLogger("codeviva")


class AppError(Exception):
    """
    Controlled application error.

    These errors are safe to expose to API clients because their
    code/message are intentionally defined by the application.
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = HTTP_400_BAD_REQUEST,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code

        super().__init__(message)


def error_response(
    code: str,
    message: str,
    status_code: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


def _status_code_to_error_code(status_code: int) -> str:
    mapping = {
        HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        HTTP_401_UNAUTHORIZED: "UNAUTHENTICATED",
        HTTP_403_FORBIDDEN: "FORBIDDEN",
        HTTP_404_NOT_FOUND: "NOT_FOUND",
        HTTP_409_CONFLICT: "CONFLICT",
        HTTP_422_UNPROCESSABLE_CONTENT: "VALIDATION_ERROR",
    }

    return mapping.get(
        status_code,
        "INTERNAL_ERROR",
    )


async def app_error_handler(
    request: Request,
    exc: AppError,
) -> JSONResponse:
    return error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    status_code = exc.status_code

    # Allow a controlled {code, message} payload when an endpoint
    # needs a domain-specific error such as EXAM_NOT_OPEN.
    if isinstance(exc.detail, dict):
        code = str(
            exc.detail.get(
                "code",
                _status_code_to_error_code(status_code),
            )
        )
        message = str(
            exc.detail.get(
                "message",
                "Request failed.",
            )
        )

        return error_response(
            code=code,
            message=message,
            status_code=status_code,
        )

    return error_response(
        code=_status_code_to_error_code(status_code),
        message=str(exc.detail),
        status_code=status_code,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return error_response(
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        status_code=HTTP_422_UNPROCESSABLE_CONTENT,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "Unhandled exception while processing %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )

    return error_response(
        code="INTERNAL_ERROR",
        message="An unexpected server error occurred.",
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )

async def starlette_http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    status_code = exc.status_code

    return error_response(
        code=_status_code_to_error_code(status_code),
        message=str(exc.detail),
        status_code=status_code,
    )

def register_error_handlers(app) -> None:
    app.add_exception_handler(
        AppError,
        app_error_handler,
    )

    app.add_exception_handler(
        HTTPException,
        http_exception_handler,
    )

    app.add_exception_handler(
        StarletteHTTPException,
        starlette_http_exception_handler,
    )

    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )

    app.add_exception_handler(
        Exception,
        unhandled_exception_handler,
    )