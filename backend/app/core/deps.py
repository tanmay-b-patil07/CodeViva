from collections.abc import Generator
from typing import Annotated, Callable
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.security import AUTH_COOKIE_NAME, decode_access_token
from app.db.models import Profile
from app.db.session import get_db


def get_database() -> Generator[Session, None, None]:
    yield from get_db()


DBSession = Annotated[Session, Depends(get_database)]


def get_current_user(
    request: Request,
    db: DBSession,
) -> Profile:
    token = request.cookies.get(AUTH_COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated.",
        )

    try:
        payload = decode_access_token(token)
        user_id = UUID(str(payload["sub"]))
    except (
        jwt.ExpiredSignatureError,
        jwt.InvalidTokenError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session.",
        ) from exc

    user = db.get(Profile, user_id)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User no longer exists.",
        )

    return user


CurrentUser = Annotated[Profile, Depends(get_current_user)]


def require_role(role: str) -> Callable:
    def dependency(
        current_user: CurrentUser,
    ) -> Profile:
        if current_user.role != role:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions.",
            )

        return current_user

    return dependency


StudentUser = Annotated[
    Profile,
    Depends(require_role("student")),
]

TeacherUser = Annotated[
    Profile,
    Depends(require_role("teacher")),
]