import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.authorization import get_student_practice_session_or_404
from app.core.config import settings
from app.core.deps import DBSession, StudentUser
from app.core.errors import AppError
from app.db.models import PracticeAnswer, PracticeQuestion, Submission
from app.schemas.practice import (
    PracticeAnswerCreate,
    PracticeAnswerResponse,
    PracticeQuestionResponse,
    PracticeSessionResponse,
)
from app.services.ai_assignment_service import evaluate_attempt

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/student/practice-sessions",
    tags=["student practice"],
)


def _question_response(question: PracticeQuestion, answer: PracticeAnswer | None):
    key: dict[str, Any] = question.answer_key or {}
    max_score = Decimal(str(key.get("max_score", "10")))
    feedback = answer.feedback if answer is not None else None
    grading_status = (
        "complete"
        if answer is not None and answer.score is not None
        else "failed"
        if feedback and feedback.startswith("AI grading failed:")
        else "pending"
    )
    return PracticeQuestionResponse(
        id=question.id,
        order_idx=question.order_idx,
        prompt=question.prompt,
        line_refs=question.line_refs,
        answer_text=answer.answer_text if answer is not None else None,
        score=answer.score if answer is not None else None,
        max_score=max_score,
        feedback=feedback,
        grading_status=grading_status,
    )


@router.get(
    "/{session_id}",
    response_model=PracticeSessionResponse,
)
def get_practice_session(
    session_id: UUID,
    current_user: StudentUser,
    db: DBSession,
) -> PracticeSessionResponse:
    session = get_student_practice_session_or_404(
        db,
        session_id,
        current_user.id,
    )
    submission = db.get(Submission, session.submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Practice code not found.")
    rows = db.execute(
        select(PracticeQuestion, PracticeAnswer)
        .outerjoin(PracticeAnswer, PracticeAnswer.question_id == PracticeQuestion.id)
        .where(PracticeQuestion.session_id == session.id)
        .order_by(PracticeQuestion.order_idx)
    ).all()
    facts = submission.code_facts or {}
    ai_status = facts.get("ai_analysis", {})
    return PracticeSessionResponse(
        id=session.id,
        status=session.status,
        created_at=session.created_at,
        code=submission.code,
        language=facts.get("language", "unknown"),
        code_facts=facts,
        questions=[
            _question_response(question, answer)
            for question, answer in rows
        ],
        error=ai_status.get("message"),
    )


@router.put(
    "/{session_id}/questions/{question_id}/answer",
    response_model=PracticeAnswerResponse,
)
def save_and_grade_practice_answer(
    session_id: UUID,
    question_id: UUID,
    payload: PracticeAnswerCreate,
    current_user: StudentUser,
    db: DBSession,
) -> PracticeAnswerResponse:
    session = get_student_practice_session_or_404(
        db,
        session_id,
        current_user.id,
    )
    if session.status != "ready":
        raise HTTPException(
            status_code=409,
            detail="Practice questions are not ready for answers.",
        )
    question = db.scalar(
        select(PracticeQuestion).where(
            PracticeQuestion.id == question_id,
            PracticeQuestion.session_id == session.id,
        )
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Practice question not found.")
    submission = db.get(Submission, session.submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Practice code not found.")

    answer = db.scalar(
        select(PracticeAnswer)
        .where(PracticeAnswer.question_id == question.id)
        .order_by(PracticeAnswer.answered_at.desc())
        .limit(1)
    )
    if answer is None:
        answer = PracticeAnswer(
            question_id=question.id,
            answer_text=payload.answer_text,
            is_correct=None,
            score=None,
            feedback=None,
        )
        db.add(answer)
    else:
        answer.answer_text = payload.answer_text
        answer.is_correct = None
        answer.score = None
        answer.feedback = None
    db.commit()
    db.refresh(answer)

    key = question.answer_key or {}
    max_score = Decimal(str(key.get("max_score", "10")))
    try:
        evaluation = evaluate_attempt(
            source_code=submission.code,
            language=(submission.code_facts or {}).get("language", "unknown"),
            answers=[
                {
                    "question_id": str(question.id),
                    "question": question.prompt,
                    "answer_text": answer.answer_text,
                    "expected_answer": key.get("expected_answer", ""),
                    "rubric": key.get("rubric", question.explanation or ""),
                    "max_score": str(max_score),
                }
            ],
            model=settings.model_practice,
        )
    except AppError as exc:
        logger.warning(
            "AI practice grading failed for answer %s: %s",
            answer.id,
            exc.code,
        )
        answer.feedback = f"AI grading failed: {exc.message}"
        db.commit()
        db.refresh(answer)
        return PracticeAnswerResponse(
            question_id=question.id,
            answer_text=answer.answer_text,
            score=None,
            max_score=max_score,
            feedback=answer.feedback,
            grading_status="failed",
        )

    graded = evaluation.evaluations[0]
    answer.score = graded.score
    answer.is_correct = graded.score >= max_score
    answer.feedback = f"{graded.feedback}\n\nEvidence: {graded.evidence}"
    db.commit()
    db.refresh(answer)
    return PracticeAnswerResponse(
        question_id=question.id,
        answer_text=answer.answer_text,
        score=answer.score,
        max_score=max_score,
        feedback=answer.feedback,
        grading_status="complete",
    )
