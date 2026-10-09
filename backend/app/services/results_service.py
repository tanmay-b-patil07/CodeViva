"""Student-safe result retrieval."""

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Answer, AttemptResult, ExamAttempt, Score
from app.schemas.grading import StudentAttemptResultResponse, StudentQuestionResult


def get_student_attempt_result(
    db: Session, attempt_id: UUID, student_id: UUID
) -> StudentAttemptResultResponse:
    attempt = db.scalar(
        select(ExamAttempt).where(
            ExamAttempt.id == attempt_id, ExamAttempt.student_id == student_id
        )
    )
    if attempt is None:
        raise AppError(
            "NOT_FOUND", "Exam attempt not found.", status.HTTP_404_NOT_FOUND
        )
    result = db.get(AttemptResult, attempt.id)
    if result is None:
        return StudentAttemptResultResponse(
            attempt_id=attempt.id,
            submitted_at=attempt.submitted_at,
            auto_submitted=attempt.auto_submitted,
            grading_status="pending",
        )
    question_results = db.execute(
        select(Answer.question_id, Score.score, Score.max_score, Score.feedback)
        .join(Score, Score.answer_id == Answer.id)
        .where(Answer.attempt_id == attempt.id)
    ).all()
    return StudentAttemptResultResponse(
        attempt_id=attempt.id,
        submitted_at=attempt.submitted_at,
        auto_submitted=attempt.auto_submitted,
        grading_status=result.status,
        total_score=result.total_score,
        max_score=result.max_score,
        percentage=result.percentage,
        graded_at=result.graded_at,
        questions=[
            StudentQuestionResult(
                question_id=question_id,
                awarded_score=score,
                max_score=max_score,
                feedback=feedback,
            )
            for question_id, score, max_score, feedback in question_results
        ]
        if result.status == "graded"
        else [],
    )
