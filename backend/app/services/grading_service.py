"""Persistence orchestration around the external grading evaluator."""

import asyncio
import inspect
import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
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

try:  # Support both application deployment and repository-root tests.
    from ai.schemas import QuestionDraft
    from ai.schemas import Score as EvaluatedScore
    from ai.scoring import CategoryMappingError, calculate_comprehension_index
except ModuleNotFoundError:  # pragma: no cover - import layout compatibility.
    from backend.ai.schemas import QuestionDraft
    from backend.ai.schemas import Score as EvaluatedScore
    from backend.ai.scoring import CategoryMappingError, calculate_comprehension_index

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


def _claim_grading(db: Session, attempt_id: UUID) -> tuple[AttemptResult, bool]:
    """Atomically acquire the short-lived right to call the grading provider.

    The claim is committed before the external request, so no transaction or
    row lock is held while waiting for the provider. PostgreSQL's primary key
    and conditional update make this safe across application processes.
    """
    claimed = db.execute(
        update(AttemptResult)
        .where(
            AttemptResult.attempt_id == attempt_id,
            AttemptResult.status.in_(("pending", "failed")),
        )
        .values(status="grading")
    ).rowcount
    if claimed:
        db.commit()
        result = db.get(AttemptResult, attempt_id)
        if result is None:  # Defensive: a committed update must retain its row.
            raise RuntimeError("Grading claim was not persisted.")
        db.refresh(result)
        return result, True

    # Older attempts may predate pending-result creation. Insert once without
    # a race; a competing insert leaves its active/existing result intact.
    inserted = db.execute(
        insert(AttemptResult)
        .values(attempt_id=attempt_id, status="grading")
        .on_conflict_do_nothing(index_elements=[AttemptResult.attempt_id])
    ).rowcount
    db.commit()
    result = db.get(AttemptResult, attempt_id)
    if result is None:
        raise RuntimeError("Grading result could not be loaded after claim.")
    db.refresh(result)
    # The caller owns only a row it updated or inserted. Existing grading and
    # graded rows are deliberately returned without another provider request.
    return result, bool(inserted)


def _record_grading_failure(
    db: Session, attempt_id: UUID, error: Exception
) -> AttemptResult:
    """Fail only an active claim; a completed grade must remain immutable."""
    db.execute(
        update(AttemptResult)
        .where(
            AttemptResult.attempt_id == attempt_id,
            AttemptResult.status == "grading",
        )
        .values(
            status="failed",
            total_score=None,
            max_score=None,
            percentage=None,
            graded_at=None,
            grading_error=str(error)[:2000],
        )
    )
    db.commit()
    failed = db.get(AttemptResult, attempt_id)
    if failed is None:
        raise RuntimeError("Grading failure state was not persisted.")
    db.refresh(failed)
    return failed


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


def _comprehension_for_result(payload: GradingAttemptInput, result: GradingResult):
    """Calculate Phase 5 data only when every question has a mapped category."""
    questions = [
        QuestionDraft(
            type=question.type,
            prompt=question.prompt,
            line_refs=[1],
            answer_format=question.answer_format,
            max_score=float(question.max_score),
            answer_key=question.answer_key,
            rubric=question.rubric,
            question_hash=str(question.id),
        )
        for question in payload.questions
    ]
    scores = [
        EvaluatedScore(
            question_id=str(grade.question_id),
            score=float(grade.awarded_score),
            max_score=float(grade.max_score),
            evidence=grade.evidence or "",
            confidence=float(grade.confidence or 0),
            needs_review=grade.needs_review,
            feedback=grade.feedback or "",
        )
        for grade in result.question_grades
    ]
    try:
        return calculate_comprehension_index(str(payload.attempt_id), questions, scores)
    except CategoryMappingError:
        # The approved config deliberately has no category for ``what_if``.
        # Preserve a successful grade without falsely claiming a complete index.
        return None


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

    existing, owns_claim = _claim_grading(db, attempt.id)
    if not owns_claim:
        # Another worker is actively grading, or a completed grade already
        # exists. Returning the persisted state is safe and idempotent.
        return existing

    payload, answers = _input_for_attempt(db, attempt)
    try:
        result = _gateway_result(payload)
        if result.attempt_id != attempt.id:
            raise ValueError(
                "Grading result attempt_id does not match the requested attempt."
            )
        expected = {question.id: question for question in payload.questions}
        received_question_ids = [grade.question_id for grade in result.question_grades]
        if len(received_question_ids) != len(expected) or set(
            received_question_ids
        ) != set(expected):
            raise ValueError(
                "Grading result must contain exactly one grade per question."
            )
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

        comprehension = _comprehension_for_result(payload, result)

        persisted = db.get(AttemptResult, attempt.id)
        if persisted is None:
            raise RuntimeError("Grading claim is no longer active.")
        db.refresh(persisted)
        if persisted.status != "grading":
            raise RuntimeError("Grading claim is no longer active.")
        persisted.status = "graded"
        persisted.total_score = result.total_score
        persisted.max_score = result.max_score
        persisted.percentage = (result.total_score / result.max_score) * Decimal(100)
        persisted.graded_at = _now()
        persisted.grading_error = None
        if comprehension is None:
            persisted.comprehension_index = None
            persisted.sub_scores = None
            persisted.flag_oral_followup = None
            persisted.needs_review_count = None
        else:
            persisted.comprehension_index = Decimal(
                str(comprehension.comprehension_index)
            )
            persisted.sub_scores = comprehension.sub_scores
            persisted.flag_oral_followup = comprehension.flag_oral_followup
            persisted.needs_review_count = comprehension.needs_review_count
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
        # Only the worker that still owns an active claim may mark it failed;
        # never overwrite a grade committed by another worker.
        return _record_grading_failure(db, attempt.id, exc)
