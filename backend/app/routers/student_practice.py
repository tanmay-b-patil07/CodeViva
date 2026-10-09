
"""Student practice-session and SSE question endpoints."""

import importlib
import json
import logging
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from ai.dedupe import hash_for_question
from app.core.authorization import (
    get_student_practice_session_or_404,
    get_student_submission_or_404,
)
from app.core.deps import DBSession, StudentUser
from app.db.models import PracticeQuestion, PracticeSession, Submission
from app.schemas.practice import (
    PracticeStartRequest,
    PracticeStartResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/student/practice", tags=["student practice"])

PRACTICE_QUESTION_COUNT = 5
DETERMINISTIC_TYPES = {"trace_output", "trace_variable", "edge_case"}


class PracticeGenerationError(RuntimeError):
    """Safe router-level error for practice-generation failures."""


def _load_practice_generator():
    """Import the generator on demand so router registration stays lightweight."""
    backend_dir = Path(__file__).resolve().parents[2]
    backend_path = str(backend_dir)

    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    try:
        module = importlib.import_module("ai.practice")
    except ModuleNotFoundError as exc:
        if exc.name not in {"ai", "ai.practice"}:
            raise
        raise PracticeGenerationError(
            "The practice generator is unavailable. Check backend/ai/practice.py."
        ) from exc

    generator = getattr(module, "stream_practice_questions", None)
    if not callable(generator):
        raise PracticeGenerationError(
            "The AI module does not expose stream_practice_questions."
        )

    return generator


def _sse(event: str, payload: dict[str, Any]) -> str:
    data = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return f"event: {event}\ndata: {data}\n\n"


def _model_data(question: Any) -> dict[str, Any]:
    if hasattr(question, "model_dump"):
        return question.model_dump(mode="json")
    if isinstance(question, dict):
        return question
    raise TypeError(
        f"Unsupported generated question type: {type(question).__name__}"
    )


def _store_answer_key(value: Any) -> dict[str, Any] | None:
    """Keep scalar answers compatible with the database's JSON-object column."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    return {"__codeviva_scalar__": value}


def _read_answer_key(value: Any) -> Any:
    if (
        isinstance(value, dict)
        and set(value) == {"__codeviva_scalar__"}
    ):
        return value["__codeviva_scalar__"]
    return value


def _question_event(
    question: PracticeQuestion,
    *,
    answer_key: Any = None,
    explanation: str | None = None,
    max_score: float = 10.0,
) -> dict[str, Any]:
    saved_key = _read_answer_key(question.answer_key)

    return {
        "id": str(question.id),
        "order_idx": question.order_idx,
        "type": question.type,
        "prompt": question.prompt,
        "line_refs": question.line_refs or [],
        "answer_format": question.answer_format,
        "options": question.options,
        "max_score": max_score,
        "answer_key": saved_key if answer_key is None else answer_key,
        "explanation": (
            question.explanation
            if explanation is None
            else explanation
        ),
    }


def _load_saved_questions(
    db: Any,
    session_id: UUID,
) -> list[PracticeQuestion]:
    return list(
        db.scalars(
            select(PracticeQuestion)
            .where(PracticeQuestion.session_id == session_id)
            .order_by(PracticeQuestion.order_idx.asc())
        ).all()
    )


@router.post(
    "",
    response_model=PracticeStartResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_practice(
    payload: PracticeStartRequest,
    current_user: StudentUser,
    db: DBSession,
) -> PracticeStartResponse:
    """Create a practice session for a submission owned by the student."""
    submission = get_student_submission_or_404(
        db,
        payload.submission_id,
        current_user.id,
    )

    session = PracticeSession(
        student_id=current_user.id,
        submission_id=submission.id,
        status="generating",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return PracticeStartResponse(
        session_id=session.id,
        status=session.status,
    )


@router.get("/{session_id}/stream")
async def stream_practice(
    session_id: UUID,
    current_user: StudentUser,
    db: DBSession,
) -> StreamingResponse:
    """Replay saved questions and stream newly generated practice questions."""
    session = get_student_practice_session_or_404(
        db,
        session_id,
        current_user.id,
    )
    submission = db.get(Submission, session.submission_id)

    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found.",
        )

    async def event_stream() -> AsyncIterator[str]:
        saved = _load_saved_questions(db, session.id)
        seen_hashes = {
            str(question.question_hash)
            for question in saved
            if question.question_hash
        }
        count = len(saved)

        # Replay saved events first so reconnecting clients can restore state.
        for question in saved:
            yield _sse("question", _question_event(question))

        if session.status == "ready":
            yield _sse("done", {"count": count})
            return

        if session.status == "failed":
            yield _sse(
                "error",
                {
                    "code": "GENERATION_FAILED",
                    "message": "Practice generation failed. Please start a new session.",
                },
            )
            return

        remaining = max(0, PRACTICE_QUESTION_COUNT - count)
        if remaining == 0:
            session.status = "ready"
            db.commit()
            yield _sse("done", {"count": count})
            return

        try:
            generate = _load_practice_generator()

            async for candidate in generate(
                submission.code,
                submission.code_facts,
                total_questions=remaining,
                avoid_hashes=seen_hashes,
            ):
                data = _model_data(candidate)
                question_hash = hash_for_question(data)

                # Final persistence-level guard against duplicate questions.
                if question_hash in seen_hashes:
                    continue

                question_type = str(data["type"])
                source = (
                    "deterministic"
                    if question_type in DETERMINISTIC_TYPES
                    else "llm"
                )

                question = PracticeQuestion(
                    session_id=session.id,
                    order_idx=count + 1,
                    type=question_type,
                    prompt=str(data["prompt"]),
                    line_refs=data.get("line_refs") or [],
                    answer_format=str(data["answer_format"]),
                    options=data.get("options"),
                    answer_key=_store_answer_key(data.get("answer_key")),
                    explanation=data.get("explanation"),
                    source=source,
                    question_hash=question_hash,
                )

                db.add(question)
                db.commit()
                db.refresh(question)

                seen_hashes.add(question_hash)
                count += 1

                # Persist before emitting the event.
                yield _sse(
                    "question",
                    _question_event(
                        question,
                        answer_key=data.get("answer_key"),
                        explanation=data.get("explanation"),
                        max_score=float(data.get("max_score", 10.0)),
                    ),
                )

            if count == 0:
                raise PracticeGenerationError(
                    "No valid practice questions were generated."
                )

            session.status = "ready"
            db.commit()
            yield _sse("done", {"count": count})

        except Exception:
            logger.exception(
                "Practice generation failed for session %s",
                session.id,
            )
            db.rollback()

            try:
                fresh_session = get_student_practice_session_or_404(
                    db,
                    session.id,
                    current_user.id,
                )
                fresh_session.status = "failed"
                db.commit()
            except Exception:
                db.rollback()

            yield _sse(
                "error",
                {
                    "code": "GENERATION_FAILED",
                    "message": (
                        "Practice questions could not be generated. "
                        "Please try again later."
                    ),
                },
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
