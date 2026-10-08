from fastapi import APIRouter, Response,status
from app.core.errors import AppError
from app.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TeacherRegisterRequest,
    UserResponse,
)
from app.auth.service import (
    authenticate_user,
    register_student,
    register_teacher,
)
from app.core.deps import DBSession, CurrentUser
from app.core.security import (
    AUTH_COOKIE_NAME,
    create_access_token,
)


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


COOKIE_MAX_AGE = 60 * 60 * 24 * 7


def user_response(user) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )


@router.post(
    "/register",
    response_model=UserResponse,
)
def register(
    data: RegisterRequest,
    db: DBSession,
) -> UserResponse:
    user = register_student(db, data)
    return user_response(user)


@router.post(
    "/register-teacher",
    response_model=UserResponse,
)
def register_teacher_endpoint(
    data: TeacherRegisterRequest,
    db: DBSession,
) -> UserResponse:
    user = register_teacher(db, data)
    return user_response(user)


@router.post(
    "/login",
    response_model=UserResponse,
)
def login(
    data: LoginRequest,
    db: DBSession,
    response: Response,
) -> UserResponse:
    user = authenticate_user(db, data)

    if user is None:
        raise AppError(
            code="UNAUTHENTICATED",
            message="Invalid email or password.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = create_access_token(
        user_id=user.id,
        role=user.role,
    )

    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
    )

    return user_response(user)


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        httponly=True,
        secure=False,
        samesite="lax",
    )

    return {"message": "Logged out successfully."}


@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: CurrentUser,
) -> UserResponse:
    return user_response(current_user)