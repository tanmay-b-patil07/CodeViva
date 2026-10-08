from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile, status

from app.core.deps import DBSession, StudentUser
from app.core.errors import AppError
from app.schemas.submissions import SubmissionResponse
from app.services.analysis_gateway import extract_facts
from sqlalchemy import select

from app.db.models import Submission
from sqlalchemy import select

from app.db.models import Submission
from app.services.submissions import (
    calculate_code_hash,
    create_submission,
    find_cached_facts,
    validate_code_size,
    validate_filename,
)


router = APIRouter(
    prefix="/student/submissions",
    tags=["student submissions"],
)


@router.post(
    "",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_submission(
    current_user: StudentUser,
    db: DBSession,
    file: UploadFile = File(...),
    assignment_id: UUID | None = Form(default=None),
) -> SubmissionResponse:
    filename = file.filename or ""

    validate_filename(filename)

    raw = await file.read()

    try:
        code = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AppError(
            code="VALIDATION_ERROR",
            message="Submitted file must be valid UTF-8 text.",
            status_code=422,
        ) from exc

    validate_code_size(code)

    code_hash = calculate_code_hash(code)

    code_facts = find_cached_facts(
        db,
        code_hash,
    )

    if code_facts is None:
        code_facts = extract_facts(code)

    submission = create_submission(
        db,
        student_id=current_user.id,
        filename=filename,
        code=code,
        assignment_id=assignment_id,
        code_facts=code_facts,
        code_hash=code_hash,
    )

    return SubmissionResponse.model_validate(submission)

@router.get(
    "",
    response_model=list[SubmissionResponse],
)
def list_submissions(
    current_user: StudentUser,
    db: DBSession,
) -> list[SubmissionResponse]:
    submissions = db.scalars(
        select(Submission)
        .where(
            Submission.student_id == current_user.id
        )
        .order_by(
            Submission.created_at.desc()
        )
    ).all()

    return [
        SubmissionResponse.model_validate(submission)
        for submission in submissions
    ]