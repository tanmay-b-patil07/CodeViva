import secrets
from fastapi import status

from app.core.errors import AppError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.models import Profile
from app.auth.schemas import LoginRequest, RegisterRequest, TeacherRegisterRequest


def get_user_by_email(
    db: Session,
    email: str,
) -> Profile | None:
    return db.scalar(
        select(Profile).where(Profile.email == email.lower())
    )


def register_student(
    db: Session,
    data: RegisterRequest,
) -> Profile:
    email = str(data.email).lower()

    existing = get_user_by_email(db, email)
    if existing is not None:
       raise AppError(
        code="CONFLICT",
        message="A user with this email already exists.",
        status_code=status.HTTP_409_CONFLICT,
    )

    user = Profile(
        email=email,
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip(),
        role="student",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def register_teacher(
    db: Session,
    data: TeacherRegisterRequest,
) -> Profile:
    if not secrets.compare_digest(
        data.invite_code,
        settings.teacher_invite_code,
    ):
        raise AppError(
            code="FORBIDDEN",
            message="Invalid teacher invite code.",
            status_code=status.HTTP_403_FORBIDDEN,
            )

    email = str(data.email).lower()

    existing = get_user_by_email(db, email)
    if existing is not None:
       raise AppError(
        code="CONFLICT",
        message="A user with this email already exists.",
        status_code=status.HTTP_409_CONFLICT,
    )

    user = Profile(
        email=email,
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip(),
        role="teacher",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    data: LoginRequest,
) -> Profile | None:
    user = get_user_by_email(
        db,
        str(data.email).lower(),
    )

    if user is None:
        return None

    if not verify_password(
        data.password,
        user.password_hash,
    ):
        return None

    return user