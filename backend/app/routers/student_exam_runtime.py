"""Student-owned, server-authoritative exam runtime endpoints."""

from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from app.core.deps import DBSession, StudentUser
from app.core.errors import AppError
from app.db.models import Answer, Exam, ExamAttempt, ExamQuestion, ExamSlot, SlotStudent
from app.schemas.exam_runtime import (
    AnswerResponse,
    AnswerSaveRequest,
    AttemptStartResponse,
    QuestionPublic,
    StudentSlotResponse,
    SubmitAttemptResponse,
)
from app.schemas.grading import StudentAttemptResultResponse
from app.services.exam_runtime_service import (
    approved_questions_ready,
    assert_attempt_writable,
    assert_slot_open,
    get_owned_attempt_or_404,
    has_valid_submission,
    server_now,
    start_attempt,
)
from app.services.grading_service import ensure_grading_pending
from app.services.results_service import get_student_attempt_result

router = APIRouter(prefix="/student", tags=["student exam runtime"])


@router.get("/slots", response_model=list[StudentSlotResponse])
def list_student_slots(
    current_user: StudentUser, db: DBSession
) -> list[StudentSlotResponse]:
    rows = db.execute(
        select(ExamSlot, Exam, SlotStudent, ExamAttempt)
        .join(Exam, Exam.id == ExamSlot.exam_id)
        .join(SlotStudent, SlotStudent.slot_id == ExamSlot.id)
        .outerjoin(
            ExamAttempt,
            (ExamAttempt.slot_id == ExamSlot.id)
            & (ExamAttempt.student_id == SlotStudent.student_id),
        )
        .where(SlotStudent.student_id == current_user.id)
        .order_by(ExamSlot.starts_at.asc())
    ).all()
    return [
        StudentSlotResponse(
            slot_id=slot.id,
            exam_id=exam.id,
            exam_title=exam.title,
            assignment_id=exam.assignment_id,
            starts_at=slot.starts_at,
            ends_at=slot.ends_at,
            duration_minutes=exam.duration_minutes,
            attempt_id=attempt.id if attempt else None,
            attempt_status=("submitted" if attempt and attempt.submitted_at else "open")
            if attempt
            else None,
            has_submission=has_valid_submission(db, slot_student, exam),
            questions_ready=approved_questions_ready(
                db, slot.id, current_user.id, exam.num_questions
            ),
        )
        for slot, exam, slot_student, attempt in rows
    ]


@router.post("/slots/{slot_id}/start", response_model=AttemptStartResponse)
def start_student_attempt(
    slot_id: UUID, current_user: StudentUser, db: DBSession
) -> AttemptStartResponse:
    now = server_now()
    attempt = start_attempt(db, slot_id, current_user.id, now)
    return AttemptStartResponse(
        attempt_id=attempt.id, deadline_at=attempt.deadline_at, server_time=now
    )


@router.get("/attempts/{attempt_id}/questions", response_model=list[QuestionPublic])
def get_attempt_questions(
    attempt_id: UUID, current_user: StudentUser, db: DBSession
) -> list[QuestionPublic]:
    attempt = get_owned_attempt_or_404(db, attempt_id, current_user.id)
    slot = db.get(ExamSlot, attempt.slot_id)
    if slot is None:
        raise AppError("NOT_FOUND", "Exam slot not found.", status.HTTP_404_NOT_FOUND)
    assert_slot_open(slot, server_now())
    if attempt.submitted_at is not None:
        raise AppError(
            "CONFLICT",
            "This exam attempt has already been submitted.",
            status.HTTP_409_CONFLICT,
        )
    questions = db.scalars(
        select(ExamQuestion)
        .where(
            ExamQuestion.slot_id == attempt.slot_id,
            ExamQuestion.student_id == current_user.id,
            ExamQuestion.status == "approved",
        )
        .order_by(ExamQuestion.order_idx)
    ).all()
    return [QuestionPublic.model_validate(question) for question in questions]


@router.put(
    "/attempts/{attempt_id}/answers/{question_id}", response_model=AnswerResponse
)
def save_answer(
    attempt_id: UUID,
    question_id: UUID,
    payload: AnswerSaveRequest,
    current_user: StudentUser,
    db: DBSession,
) -> AnswerResponse:
    attempt = get_owned_attempt_or_404(db, attempt_id, current_user.id)
    assert_attempt_writable(attempt, server_now())
    question = db.scalar(
        select(ExamQuestion).where(
            ExamQuestion.id == question_id,
            ExamQuestion.slot_id == attempt.slot_id,
            ExamQuestion.student_id == current_user.id,
            ExamQuestion.status == "approved",
        )
    )
    if question is None:
        raise AppError(
            "NOT_FOUND", "Exam question not found.", status.HTTP_404_NOT_FOUND
        )
    answer = db.scalar(
        select(Answer).where(
            Answer.attempt_id == attempt.id, Answer.question_id == question.id
        )
    )
    if answer is None:
        answer = Answer(
            attempt_id=attempt.id,
            question_id=question.id,
            answer_text=payload.answer_text,
            saved_at=server_now(),
        )
        db.add(answer)
    else:
        answer.answer_text = payload.answer_text
        answer.saved_at = server_now()
    db.commit()
    db.refresh(answer)
    return AnswerResponse.model_validate(answer)


@router.post("/attempts/{attempt_id}/submit", response_model=SubmitAttemptResponse)
def submit_attempt(
    attempt_id: UUID, current_user: StudentUser, db: DBSession
) -> SubmitAttemptResponse:
    attempt = get_owned_attempt_or_404(db, attempt_id, current_user.id)
    if attempt.submitted_at is None:
        now = server_now()
        assert_attempt_writable(attempt, now)
        attempt.submitted_at = now
        attempt.auto_submitted = False
        ensure_grading_pending(db, attempt)
        db.commit()
        db.refresh(attempt)
    return SubmitAttemptResponse(
        attempt_id=attempt.id,
        submitted_at=attempt.submitted_at,
        auto_submitted=attempt.auto_submitted,
    )


@router.get(
    "/attempts/{attempt_id}/result", response_model=StudentAttemptResultResponse
)
def get_attempt_result(
    attempt_id: UUID, current_user: StudentUser, db: DBSession
) -> StudentAttemptResultResponse:
    return get_student_attempt_result(db, attempt_id, current_user.id)
