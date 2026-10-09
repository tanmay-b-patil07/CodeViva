import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Submission

ALLOWED_EXTENSIONS = {".py"}

# The project documentation requires upload-size validation,
# but does not prescribe a numeric limit. Keep it configurable
# rather than hard-coding an undocumented project requirement.
DEFAULT_MAX_CODE_BYTES = 1_000_000


def normalize_source(code: str) -> str:
    """
    Normalize line endings and trailing whitespace for hashing.

    The original source is still stored separately.
    """
    normalized = code.replace("\r\n", "\n").replace("\r", "\n")

    return "\n".join(
        line.rstrip()
        for line in normalized.split("\n")
    )


def calculate_code_hash(code: str) -> str:
    normalized = normalize_source(code)

    digest = hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()

    return f"sha256:{digest}"


def validate_filename(filename: str) -> None:
    filename = filename.strip()

    if not filename:
        raise AppError(
            code="VALIDATION_ERROR",
            message="Filename is required.",
            status_code=422,
        )

    extension = ""

    if "." in filename:
        extension = "." + filename.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise AppError(
            code="VALIDATION_ERROR",
            message="Only Python (.py) files are supported.",
            status_code=422,
        )


def validate_code_size(code: str) -> None:
    size = len(code.encode("utf-8"))

    if size > DEFAULT_MAX_CODE_BYTES:
        raise AppError(
            code="VALIDATION_ERROR",
            message="Submitted code exceeds the maximum allowed size.",
            status_code=422,
        )


def find_cached_facts(
    db: Session,
    code_hash: str,
    *,
    student_id: UUID,
    assignment_id: UUID | None,
) -> dict | None:
    """
    Return facts only from the same student's same assignment context.

    Source hashes alone are not an authorization boundary: derived facts can
    contain user-specific metadata, so cache hits must not cross owners or
    assignments.
    """
    submission = db.scalar(
        select(Submission)
        .where(
            Submission.code_hash == code_hash,
            Submission.student_id == student_id,
            Submission.assignment_id == assignment_id,
            Submission.code_facts.is_not(None),
        )
        .order_by(Submission.created_at.desc())
    )

    if submission is None:
        return None

    return submission.code_facts


def create_submission(
    db: Session,
    *,
    student_id: UUID,
    filename: str,
    code: str,
    assignment_id: UUID | None,
    code_facts: dict,
    code_hash: str,
) -> Submission:
    submission = Submission(
        assignment_id=assignment_id,
        student_id=student_id,
        filename=filename.strip(),
        code=code,
        code_hash=code_hash,
        code_facts=code_facts,
    )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    return submission
