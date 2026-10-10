import json
import logging
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import DBSession, StudentUser
from app.core.errors import AppError
from app.db.models import (
    Assignment,
    ExamAttempt,
    ExamQuestion,
    PracticeQuestion,
    PracticeSession,
    Submission,
)
from app.schemas.assignments import CodeSubmissionCreate
from app.schemas.submissions import SubmissionResponse
from app.services.ai_assignment_service import analyze_assignment_code
from app.services.analysis_gateway import extract_facts
from app.services.assignment_workflow import (
    get_student_assignment_context,
    split_assignment_description,
)
from app.services.submissions import (
    DEFAULT_MAX_CODE_BYTES,
    LANGUAGE_EXTENSIONS,
    calculate_code_hash,
    find_cached_facts,
    language_for_filename,
    validate_code_size,
)

router = APIRouter(
    prefix="/student/submissions",
    tags=["student submissions"],
)

logger = logging.getLogger(__name__)

MAX_AI_SOURCE_BYTES = 50_000


def _create_analyzed_submission(
    *,
    code: str,
    language: str,
    assignment_id: UUID | None,
    current_user: StudentUser,
    db: DBSession,
    filename: str,
) -> SubmissionResponse:
    validate_code_size(code)
    if len(code.encode("utf-8")) > MAX_AI_SOURCE_BYTES:
        raise AppError(
            code="VALIDATION_ERROR",
            message="AI-assisted submissions must be 50,000 UTF-8 bytes or smaller.",
            status_code=422,
        )

    assignment = exam = slot = None
    instructions = None
    if assignment_id is not None:
        assignment, exam, slot, _group = get_student_assignment_context(
            db,
            assignment_id,
            current_user.id,
        )
        if assignment.due_at is not None and assignment.due_at <= datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The deadline for this assignment has passed.",
            )
        if assignment.language != language:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Code language must match the assignment language.",
            )
        existing_attempt = db.scalar(
            select(ExamAttempt.id).where(
                ExamAttempt.slot_id == slot.id,
                ExamAttempt.student_id == current_user.id,
            )
        )
        released_question = db.scalar(
            select(ExamQuestion.id).where(
                ExamQuestion.slot_id == slot.id,
                ExamQuestion.student_id == current_user.id,
                ExamQuestion.status == "approved",
            ).limit(1)
        )
        if existing_attempt is not None or released_question is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Code cannot be changed after questions have been released.",
            )
        description, instructions = split_assignment_description(
            assignment.description
        )
        assignment_title = assignment.title
        assignment_instructions = "\n".join(
            part for part in (description, instructions) if part
        ) or None
    else:
        assignment_title = "Public code practice"
        assignment_instructions = None

    code_hash = calculate_code_hash(code)
    cached_code_facts = find_cached_facts(
        db,
        code_hash,
        student_id=current_user.id,
        assignment_id=assignment_id,
        language=language,
    )
    submission = Submission(
        assignment_id=assignment_id,
        student_id=current_user.id,
        filename=filename,
        code=code,
        code_hash=code_hash,
        code_facts={
            "language": language,
            "code_hash": code_hash,
            "ai_analysis": {"status": "pending"},
        },
    )
    db.add(submission)
    db.flush()
    practice_session = None
    if assignment_id is None:
        practice_session = PracticeSession(
            student_id=current_user.id,
            submission_id=submission.id,
            status="generating",
        )
        db.add(practice_session)
        db.flush()
    db.commit()
    db.refresh(submission)
    if practice_session is not None:
        db.refresh(practice_session)

    code_facts = cached_code_facts
    if code_facts is None:
        try:
            code_facts = extract_facts(code, language)
        except (RuntimeError, TypeError):
            logger.exception(
                "Code analysis failed after saving submission %s",
                submission.id,
            )
            message = "Code was saved, but code analysis could not be completed."
            submission.code_facts = {
                "language": language,
                "code_hash": code_hash,
                "ai_analysis": {"status": "failed", "message": message},
            }
            if practice_session is not None:
                practice_session.status = "failed"
            db.commit()
            db.refresh(submission)
            return SubmissionResponse(
                id=submission.id,
                assignment_id=submission.assignment_id,
                filename=submission.filename,
                code_hash=submission.code_hash,
                code_facts=submission.code_facts,
                created_at=submission.created_at,
                ai_analysis_status="failed",
                ai_analysis_error=message,
                practice_session_id=(
                    practice_session.id if practice_session is not None else None
                ),
            )
    else:
        code_facts = {
            key: value
            for key, value in code_facts.items()
            if key not in {"ai_review", "ai_analysis"}
        }
    assessment = None
    try:
        assessment = analyze_assignment_code(
            code=code,
            language=language,
            title=assignment_title,
            instructions=assignment_instructions,
            code_facts=code_facts,
            generate_questions=True,
            model=(
                settings.model_practice
                if assignment_id is None
                else settings.model_exam
            ),
        )
    except AppError as exc:
        submission.code_facts = {
            **code_facts,
            "ai_analysis": {"status": "failed", "message": exc.message},
        }
        if practice_session is not None:
            practice_session.status = "failed"
        db.commit()
        db.refresh(submission)
        return SubmissionResponse(
            id=submission.id,
            assignment_id=submission.assignment_id,
            filename=submission.filename,
            code_hash=submission.code_hash,
            code_facts=submission.code_facts,
            created_at=submission.created_at,
            ai_analysis_status="failed",
            ai_analysis_error=exc.message,
            practice_session_id=(
                practice_session.id if practice_session is not None else None
            ),
        )

    if assessment is None:
        raise RuntimeError("AI analysis did not produce an assessment.")
    submission.code_facts = {
        **code_facts,
        "ai_review": assessment.code_review.model_dump(mode="json"),
        "ai_analysis": {"status": "complete"},
    }
    db.flush()

    if assignment is not None and exam is not None and slot is not None:
        current_order = db.scalar(
            select(ExamQuestion.order_idx)
            .where(
                ExamQuestion.slot_id == slot.id,
                ExamQuestion.student_id == current_user.id,
            )
            .order_by(ExamQuestion.order_idx.desc())
            .limit(1)
        ) or 0
        for offset, draft in enumerate(assessment.questions, start=1):
            private_answer = {"expected_answer": draft.expected_answer}
            private_rubric = {"criteria": draft.rubric}
            hash_body = json.dumps(
                {
                    "prompt": draft.prompt,
                    "answer_key": private_answer,
                    "rubric": private_rubric,
                    "submission_id": str(submission.id),
                },
                sort_keys=True,
            )
            db.add(
                ExamQuestion(
                    exam_id=exam.id,
                    slot_id=slot.id,
                    student_id=current_user.id,
                    submission_id=submission.id,
                    order_idx=current_order + offset,
                    type="short_answer",
                    prompt=draft.prompt,
                    line_refs=[{"line": line} for line in draft.line_refs],
                    answer_format="text",
                    options=None,
                    answer_key=private_answer,
                    rubric=private_rubric,
                    max_score=draft.max_score,
                    status="draft",
                    question_hash="sha256:" + sha256(hash_body.encode()).hexdigest(),
                )
            )

    practice_questions = []
    if practice_session is not None:
        for order_idx, draft in enumerate(assessment.questions, start=1):
            hash_body = json.dumps(
                {
                    "prompt": draft.prompt,
                    "answer": draft.expected_answer,
                    "source": str(submission.id),
                },
                sort_keys=True,
            )
            practice_question = PracticeQuestion(
                session_id=practice_session.id,
                order_idx=order_idx,
                type="short_answer",
                prompt=draft.prompt,
                line_refs=[{"line": line} for line in draft.line_refs],
                answer_format="text",
                options=None,
                answer_key={
                    "expected_answer": draft.expected_answer,
                    "rubric": draft.rubric,
                    "max_score": str(draft.max_score),
                },
                explanation=draft.rubric,
                source="llm",
                question_hash="sha256:" + sha256(hash_body.encode()).hexdigest(),
            )
            db.add(practice_question)
            practice_questions.append(practice_question)
        practice_session.status = "ready"

    db.commit()
    db.refresh(submission)
    return SubmissionResponse(
        id=submission.id,
        assignment_id=submission.assignment_id,
        filename=submission.filename,
        code_hash=submission.code_hash,
        code_facts=submission.code_facts,
        created_at=submission.created_at,
        ai_analysis_status="complete",
        practice_session_id=(
            practice_session.id if practice_session is not None else None
        ),
        practice_questions=[
            {
                "id": question.id,
                "order_idx": question.order_idx,
                "prompt": question.prompt,
                "line_refs": question.line_refs,
            }
            for question in practice_questions
        ],
    )


@router.post(
    "/code",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_code(
    payload: CodeSubmissionCreate,
    current_user: StudentUser,
    db: DBSession,
) -> SubmissionResponse:
    language = payload.language.strip().lower()
    if language not in LANGUAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported code language.",
        )
    extension = LANGUAGE_EXTENSIONS[language][0]
    return _create_analyzed_submission(
        code=payload.code,
        language=language,
        assignment_id=payload.assignment_id,
        current_user=current_user,
        db=db,
        filename="solution" + extension,
    )


@router.post(
    "",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_submission(
    current_user: StudentUser,
    db: DBSession,
    file: Annotated[UploadFile, File(...)],
    assignment_id: Annotated[UUID | None, Form()] = None,
) -> SubmissionResponse:
    if assignment_id is not None and db.get(Assignment, assignment_id) is None:
        raise AppError(
            code="NOT_FOUND",
            message="Assignment not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    filename = file.filename or ""
    language = language_for_filename(filename)
    raw = await file.read(DEFAULT_MAX_CODE_BYTES + 1)
    try:
        code = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AppError(
            code="VALIDATION_ERROR",
            message="Submitted file must be valid UTF-8 text.",
            status_code=422,
        ) from exc
    return _create_analyzed_submission(
        code=code,
        language=language,
        assignment_id=assignment_id,
        current_user=current_user,
        db=db,
        filename=filename,
    )


@router.get("", response_model=list[SubmissionResponse])
def list_submissions(
    current_user: StudentUser,
    db: DBSession,
) -> list[SubmissionResponse]:
    submissions = db.scalars(
        select(Submission)
        .where(Submission.student_id == current_user.id)
        .order_by(Submission.created_at.desc())
    ).all()
    return [
        SubmissionResponse(
            id=submission.id,
            assignment_id=submission.assignment_id,
            filename=submission.filename,
            code_hash=submission.code_hash,
            code_facts=submission.code_facts,
            created_at=submission.created_at,
            ai_analysis_status=submission.code_facts.get(
                "ai_analysis", {}
            ).get("status", "complete" if submission.code_facts.get("ai_review") else "pending"),
            ai_analysis_error=submission.code_facts.get(
                "ai_analysis", {}
            ).get("message"),
        )
        for submission in submissions
    ]
