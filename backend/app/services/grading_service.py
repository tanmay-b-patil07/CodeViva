"""Persistence orchestration around the external grading evaluator."""

import asyncio
import inspect
import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Answer, AttemptResult, ExamAttempt, ExamQuestion, Score
from app.schemas.grading import (
    GradingAnswerInput,
    GradingAttemptInput,
    GradingQuestionInput,
    GradingResult,
)
from app.services import grading_gateway

logger = logging.getLogger("codeviva.grading")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_grading_pending(db: Session, attempt: ExamAttempt) -> AttemptResult:
    """Persist the deferred-grading state without invoking the evaluator."""
    result = db.get(AttemptResult, attempt.id)
    if result is None:
        result = AttemptResult(attempt_id=attempt.id, status="pending")
        db.add(result)
    return result


def _gateway_result(payload: GradingAttemptInput) -> GradingResult:
    result = grading_gateway.grade_attempt(payload)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    return GradingResult.model_validate(result)


def _input_for_attempt(
    db: Session, attempt: ExamAttempt
) -> tuple[GradingAttemptInput, dict[UUID, Answer]]:
    questions = db.scalars(
        select(ExamQuestion)
        .where(
            ExamQuestion.slot_id == attempt.slot_id,
            ExamQuestion.student_id == attempt.student_id,
            ExamQuestion.status == "approved",
        )
        .order_by(ExamQuestion.order_idx)
    ).all()
    answers = {
        answer.question_id: answer
        for answer in db.scalars(
            select(Answer).where(Answer.attempt_id == attempt.id)
        ).all()
    }
    return (
        GradingAttemptInput(
            attempt_id=attempt.id,
            student_id=attempt.student_id,
            slot_id=attempt.slot_id,
            questions=[
                GradingQuestionInput(
                    id=question.id,
                    prompt=question.prompt,
                    type=question.type,
                    answer_format=question.answer_format,
                    answer_key=question.answer_key,
                    rubric=question.rubric,
                    max_score=question.max_score,
                    answer=(
                        GradingAnswerInput(
                            question_id=question.id,
                            answer_id=answers[question.id].id,
                            answer_text=answers[question.id].answer_text,
                        )
                        if question.id in answers
                        else None
                    ),
                )
                for question in questions
            ],
        ),
        answers,
    )


def grade_submitted_attempt(db: Session, attempt_id: UUID) -> AttemptResult:
    """Grade one finalised attempt; duplicate calls return its existing result."""
    attempt = db.get(ExamAttempt, attempt_id)
    if attempt is None:
        raise AppError(
            "NOT_FOUND", "Exam attempt not found.", status.HTTP_404_NOT_FOUND
        )
    if attempt.submitted_at is None:
        raise AppError(
            "ATTEMPT_NOT_SUBMITTED",
            "Exam attempt must be submitted before grading.",
            status.HTTP_409_CONFLICT,
        )

    existing = db.get(AttemptResult, attempt.id)
    if existing is not None and existing.status == "graded":
        return existing

    payload, answers = _input_for_attempt(db, attempt)
    try:
        result = _gateway_result(payload)
        if result.attempt_id != attempt.id:
            raise ValueError(
                "Grading result attempt_id does not match the requested attempt."
            )
        expected = {question.id: question for question in payload.questions}
        total_from_questions = Decimal(0)
        for grade in result.question_grades:
            question = expected.get(grade.question_id)
            if question is None:
                raise ValueError("Grading result contains an unknown question.")
            if (
                grade.awarded_score > grade.max_score
                or grade.max_score != question.max_score
            ):
                raise ValueError("Grading result contains invalid question scores.")
            total_from_questions += grade.awarded_score
        if result.total_score > result.max_score or result.max_score != sum(
            (q.max_score for q in payload.questions), Decimal(0)
        ):
            raise ValueError("Grading result contains invalid total scores.")
        if result.question_grades and total_from_questions != result.total_score:
            raise ValueError("Grading result total does not match question scores.")

        persisted = existing or AttemptResult(attempt_id=attempt.id, status="grading")
        persisted.status = "graded"
        persisted.total_score = result.total_score
        persisted.max_score = result.max_score
        persisted.percentage = (result.total_score / result.max_score) * Decimal(100)
        persisted.graded_at = _now()
        persisted.grading_error = None
        db.add(persisted)
        db.flush()
        for grade in result.question_grades:
            answer = answers.get(grade.question_id)
            # Scores are answer-owned in the existing schema; unanswered
            # questions remain represented in the total but have no Score row.
            if answer is None:
                continue
            score = db.scalar(select(Score).where(Score.answer_id == answer.id))
            if score is None:
                score = Score(
                    answer_id=answer.id,
                    score=grade.awarded_score,
                    max_score=grade.max_score,
                    evidence=grade.evidence or "",
                    confidence=grade.confidence
                    if grade.confidence is not None
                    else Decimal(0),
                    needs_review=grade.needs_review,
                    feedback=grade.feedback or "",
                )
                db.add(score)
            else:
                score.score = grade.awarded_score
                score.max_score = grade.max_score
                score.evidence = grade.evidence or ""
                score.confidence = (
                    grade.confidence if grade.confidence is not None else Decimal(0)
                )
                score.needs_review = grade.needs_review
                score.feedback = grade.feedback or ""
        db.commit()
        db.refresh(persisted)
        return persisted
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001 - persist grading failure for retry/inspection.
        db.rollback()
        logger.error(
            "Grading failed for attempt=%s (type=%s)",
            attempt.id,
            type(exc).__name__,
        )
        failed = db.get(AttemptResult, attempt.id) or AttemptResult(
            attempt_id=attempt.id, status="failed"
        )
        failed.status = "failed"
        failed.total_score = None
        failed.max_score = None
        failed.percentage = None
        failed.graded_at = None
        failed.grading_error = str(exc)[:2000]
        db.add(failed)
        db.commit()
        return failed
