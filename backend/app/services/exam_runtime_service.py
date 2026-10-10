"""Server-authoritative student exam runtime helpers (no grading)."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.db.models import (
    Exam,
    ExamAttempt,
    ExamQuestion,
    ExamSlot,
    SlotStudent,
    Submission,
)
from app.services.grading_service import ensure_grading_pending

logger = logging.getLogger("codeviva.exam_runtime")


def server_now() -> datetime:
    return datetime.now(timezone.utc)


def _error(code: str, message: str, status_code: int) -> None:
    raise AppError(code=code, message=message, status_code=status_code)


def get_student_slot_or_404(
    db: Session, slot_id: UUID, student_id: UUID
) -> tuple[ExamSlot, Exam, SlotStudent]:
    row = db.execute(
        select(ExamSlot, Exam, SlotStudent)
        .join(Exam, Exam.id == ExamSlot.exam_id)
        .join(SlotStudent, SlotStudent.slot_id == ExamSlot.id)
        .where(ExamSlot.id == slot_id, SlotStudent.student_id == student_id)
    ).first()
    if row is None:
        _error("NOT_FOUND", "Exam slot not found.", status.HTTP_404_NOT_FOUND)
    return row


def has_valid_submission(db: Session, slot_student: SlotStudent, exam: Exam) -> bool:
    if slot_student.submission_id is not None:
        return (
            db.scalar(
                select(Submission.id).where(
                    Submission.id == slot_student.submission_id,
                    Submission.student_id == slot_student.student_id,
                    Submission.assignment_id == exam.assignment_id,
                )
            )
            is not None
        )
    return (
        db.scalar(
            select(Submission.id).where(
                Submission.student_id == slot_student.student_id,
                Submission.assignment_id == exam.assignment_id,
            )
        )
        is not None
    )


def approved_questions_ready(
    db: Session, slot_id: UUID, student_id: UUID, expected: int | None = None
) -> bool:
    count = len(
        db.scalars(
            select(ExamQuestion.id).where(
                ExamQuestion.slot_id == slot_id,
                ExamQuestion.student_id == student_id,
                ExamQuestion.status == "approved",
            )
        ).all()
    )
    return count >= (expected or 1)


def assert_slot_open(slot: ExamSlot, now: datetime) -> None:
    if now < slot.starts_at:
        _error(
            "EXAM_NOT_OPEN", "The exam window has not opened.", status.HTTP_409_CONFLICT
        )
    if now > slot.ends_at:
        _error("EXAM_CLOSED", "The exam window has closed.", status.HTTP_409_CONFLICT)


def start_attempt(
    db: Session, slot_id: UUID, student_id: UUID, now: datetime | None = None
) -> ExamAttempt:
    current_time = now or server_now()
    slot, exam, slot_student = get_student_slot_or_404(db, slot_id, student_id)
    assert_slot_open(slot, current_time)
    existing = db.scalar(
        select(ExamAttempt).where(
            ExamAttempt.slot_id == slot_id, ExamAttempt.student_id == student_id
        )
    )
    if existing is not None:
        return existing
    if not has_valid_submission(db, slot_student, exam):
        _error(
            "NO_SUBMISSION",
            "No eligible submission is linked to this exam.",
            status.HTTP_409_CONFLICT,
        )
    if not approved_questions_ready(db, slot_id, student_id, exam.num_questions):
        _error(
            "QUESTIONS_NOT_READY",
            "Approved exam questions are not ready.",
            status.HTTP_409_CONFLICT,
        )
    attempt = ExamAttempt(
        slot_id=slot.id,
        student_id=student_id,
        started_at=current_time,
        deadline_at=min(
            current_time + timedelta(minutes=exam.duration_minutes), slot.ends_at
        ),
    )
    try:
        with db.begin_nested():
            db.add(attempt)
            db.flush()
    except IntegrityError:
        existing = db.scalar(
            select(ExamAttempt).where(
                ExamAttempt.slot_id == slot_id, ExamAttempt.student_id == student_id
            )
        )
        if existing is None:
            raise
        return existing
    db.commit()
    db.refresh(attempt)
    return attempt


def assert_attempt_writable(attempt: ExamAttempt, now: datetime) -> None:
    if attempt.submitted_at is not None:
        _error(
            "CONFLICT",
            "This exam attempt has already been submitted.",
            status.HTTP_409_CONFLICT,
        )
    if now > attempt.deadline_at + timedelta(seconds=settings.exam_grace_seconds):
        _error(
            "EXAM_CLOSED", "The attempt deadline has passed.", status.HTTP_409_CONFLICT
        )


def get_owned_attempt_or_404(
    db: Session, attempt_id: UUID, student_id: UUID
) -> ExamAttempt:
    attempt = db.scalar(
        select(ExamAttempt).where(
            ExamAttempt.id == attempt_id, ExamAttempt.student_id == student_id
        )
    )
    if attempt is None:
        _error("NOT_FOUND", "Exam attempt not found.", status.HTTP_404_NOT_FOUND)
    return attempt


def autosubmit_expired_attempts(now: datetime | None = None) -> int:
    """Finalize expired attempts only; grading belongs to Phase 12."""
    from app.db.session import SessionLocal

    current_time = now or server_now()
    db = SessionLocal()
    submitted = 0
    try:
        attempts = db.scalars(
            select(ExamAttempt).where(
                ExamAttempt.submitted_at.is_(None),
                ExamAttempt.deadline_at < current_time,
            )
        ).all()
        for attempt in attempts:
            try:
                with db.begin_nested():
                    attempt.submitted_at = current_time
                    attempt.auto_submitted = True
                    # Auto-submitted attempts follow the same deferred grading
                    # lifecycle as a normal final submission.
                    ensure_grading_pending(db, attempt)
                    db.flush()
                submitted += 1
            except Exception as exc:  # noqa: BLE001 - isolate each expired attempt.
                logger.error(
                    "Auto-submit failed for attempt=%s (type=%s)",
                    attempt.id,
                    type(exc).__name__,
                )
                continue
        db.commit()
        return submitted
    finally:
        db.close()
