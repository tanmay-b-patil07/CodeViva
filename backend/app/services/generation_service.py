"""Member 1 orchestration for per-student exam-question generation."""

import asyncio
import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models import Exam, ExamQuestion, ExamSlot, SlotStudent, Submission
from app.db.session import SessionLocal
from app.services import exam_generation_gateway

logger = logging.getLogger("codeviva.generation")


def _question_value(question: Any, name: str, default: Any = None) -> Any:
    if isinstance(question, dict):
        return question.get(name, default)
    return getattr(question, name, default)


def _create_failed_marker(
    db,
    *,
    exam: Exam,
    slot_id: UUID,
    student_id: UUID,
    submission_id: UUID,
) -> None:
    """Record a recoverable, server-only failure for a resolved submission."""
    db.add(
        ExamQuestion(
            exam_id=exam.id,
            slot_id=slot_id,
            student_id=student_id,
            submission_id=submission_id,
            order_idx=0,
            type="generation_error",
            prompt="",
            line_refs=[],
            answer_format="none",
            options=None,
            answer_key=None,
            rubric=None,
            max_score=Decimal(0),
            status="failed",
            question_hash=f"failed:{slot_id}:{student_id}",
        )
    )


def _resolve_submission(
    db,
    *,
    slot_student: SlotStudent,
    assignment_id: UUID,
) -> Submission | None:
    if slot_student.submission_id is not None:
        return db.scalar(
            select(Submission).where(
                Submission.id == slot_student.submission_id,
                Submission.student_id == slot_student.student_id,
                Submission.assignment_id == assignment_id,
            )
        )

    submission = db.scalar(
        select(Submission)
        .where(
            Submission.student_id == slot_student.student_id,
            Submission.assignment_id == assignment_id,
        )
        .order_by(Submission.created_at.desc())
    )
    if submission is not None:
        slot_student.submission_id = submission.id
    return submission


def generate_for_student(slot_id: UUID, student_id: UUID) -> None:
    """Generate and persist one student's questions in an isolated DB session."""
    db = SessionLocal()
    try:
        slot = db.get(ExamSlot, slot_id)
        if slot is None:
            logger.warning("Generation skipped: slot %s no longer exists", slot_id)
            return
        exam = db.get(Exam, slot.exam_id)
        slot_student = db.get(SlotStudent, (slot_id, student_id))
        if exam is None or slot_student is None:
            logger.warning("Generation skipped for slot=%s student=%s", slot_id, student_id)
            return

        submission = _resolve_submission(
            db,
            slot_student=slot_student,
            assignment_id=exam.assignment_id,
        )
        if submission is None:
            db.commit()
            logger.warning(
                "Generation skipped for slot=%s student=%s: no valid assignment submission",
                slot_id,
                student_id,
            )
            return

        avoid_hashes = set(
            db.scalars(
                select(ExamQuestion.question_hash).where(
                    ExamQuestion.exam_id == exam.id,
                    ExamQuestion.student_id == student_id,
                )
            ).all()
        )
        try:
            questions = asyncio.run(
                exam_generation_gateway.generate_exam_questions(
                    code=submission.code,
                    facts=submission.code_facts,
                    n=exam.num_questions,
                    avoid_hashes=avoid_hashes,
                )
            )
        except Exception as exc:  # noqa: BLE001 - isolate external generation failures.
            _create_failed_marker(
                db,
                exam=exam,
                slot_id=slot_id,
                student_id=student_id,
                submission_id=submission.id,
            )
            db.commit()
            logger.error(
                "Question generation failed for slot=%s exam=%s student=%s (type=%s)",
                slot_id,
                exam.id,
                student_id,
                type(exc).__name__,
            )
            return

        try:
            if not questions:
                raise ValueError("Member 3 returned no exam questions.")
            status = "approved" if exam.auto_approve else "draft"
            for order_idx, question in enumerate(questions, start=1):
                db.add(
                    ExamQuestion(
                        exam_id=exam.id,
                        slot_id=slot_id,
                        student_id=student_id,
                        submission_id=submission.id,
                        order_idx=order_idx,
                        type=_question_value(question, "type"),
                        prompt=_question_value(question, "prompt"),
                        line_refs=_question_value(question, "line_refs", []),
                        answer_format=_question_value(question, "answer_format"),
                        options=_question_value(question, "options"),
                        answer_key=_question_value(question, "answer_key"),
                        rubric=_question_value(question, "rubric"),
                        max_score=Decimal(str(_question_value(question, "max_score"))),
                        status=status,
                        question_hash=_question_value(question, "question_hash"),
                    )
                )
            db.commit()
        except Exception as exc:  # noqa: BLE001 - persist a safe failure marker.
            db.rollback()
            _create_failed_marker(
                db,
                exam=exam,
                slot_id=slot_id,
                student_id=student_id,
                submission_id=submission.id,
            )
            db.commit()
            logger.error(
                "Question persistence failed for slot=%s exam=%s student=%s (type=%s)",
                slot_id,
                exam.id,
                student_id,
                type(exc).__name__,
            )
    except Exception as exc:  # noqa: BLE001 - isolate one student's workflow.
        db.rollback()
        logger.error(
            "Unexpected generation orchestration failure for slot=%s student=%s (type=%s)",
            slot_id,
            student_id,
            type(exc).__name__,
        )
    finally:
        db.close()
