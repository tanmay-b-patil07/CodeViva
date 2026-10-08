from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Assignment,
    Exam,
    ExamAttempt,
    ExamSlot,
    Group,
    PracticeSession,
    Submission,
)


def get_owned_group_or_404(
    db: Session,
    group_id: UUID,
    teacher_id: UUID,
) -> Group:
    """Return a group only when it belongs to the given teacher."""
    group = db.scalar(
        select(Group).where(
            Group.id == group_id,
            Group.teacher_id == teacher_id,
        )
    )

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found.",
        )

    return group


def get_owned_assignment_or_404(
    db: Session,
    assignment_id: UUID,
    teacher_id: UUID,
) -> Assignment:
    """Return an assignment only when it belongs to the given teacher."""
    assignment = db.scalar(
        select(Assignment).where(
            Assignment.id == assignment_id,
            Assignment.teacher_id == teacher_id,
        )
    )

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found.",
        )

    return assignment


def get_owned_exam_or_404(
    db: Session,
    exam_id: UUID,
    teacher_id: UUID,
) -> Exam:
    """Return an exam only when it belongs to the given teacher."""
    exam = db.scalar(
        select(Exam).where(
            Exam.id == exam_id,
            Exam.teacher_id == teacher_id,
        )
    )

    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found.",
        )

    return exam


def get_owned_exam_slot_or_404(
    db: Session,
    slot_id: UUID,
    teacher_id: UUID,
) -> ExamSlot:
    """Return a slot only when its exam belongs to the given teacher."""
    slot = db.scalar(
        select(ExamSlot)
        .join(Exam, Exam.id == ExamSlot.exam_id)
        .where(
            ExamSlot.id == slot_id,
            Exam.teacher_id == teacher_id,
        )
    )

    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam slot not found.",
        )

    return slot


def get_student_submission_or_404(
    db: Session,
    submission_id: UUID,
    student_id: UUID,
) -> Submission:
    """Return a submission only when it belongs to the student."""
    submission = db.scalar(
        select(Submission).where(
            Submission.id == submission_id,
            Submission.student_id == student_id,
        )
    )

    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found.",
        )

    return submission


def get_student_practice_session_or_404(
    db: Session,
    session_id: UUID,
    student_id: UUID,
) -> PracticeSession:
    """Return a practice session only when it belongs to the student."""
    session = db.scalar(
        select(PracticeSession).where(
            PracticeSession.id == session_id,
            PracticeSession.student_id == student_id,
        )
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practice session not found.",
        )

    return session


def get_student_attempt_or_404(
    db: Session,
    attempt_id: UUID,
    student_id: UUID,
) -> ExamAttempt:
    """Return an exam attempt only when it belongs to the student."""
    attempt = db.scalar(
        select(ExamAttempt).where(
            ExamAttempt.id == attempt_id,
            ExamAttempt.student_id == student_id,
        )
    )

    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam attempt not found.",
        )

    return attempt