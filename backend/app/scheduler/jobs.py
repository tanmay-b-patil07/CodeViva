"""APScheduler jobs that decide when Phase 9 generation should run."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.db.models import ExamQuestion, ExamSlot, SlotStudent
from app.db.session import SessionLocal
from app.services import generation_service
from app.services.exam_runtime_service import autosubmit_expired_attempts

logger = logging.getLogger("codeviva.scheduler")


def _student_has_generation_record(db, slot_id: UUID, student_id: UUID) -> bool:
    """Phase 9 treats any existing terminal/in-progress question record as claimed."""
    return (
        db.scalar(
            select(ExamQuestion.id).where(
                ExamQuestion.slot_id == slot_id,
                ExamQuestion.student_id == student_id,
            )
        )
        is not None
    )


def run_generation_discovery(now: datetime | None = None) -> int:
    """Find due, not-yet-started slots and delegate missing students to Phase 9."""
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("Scheduler timestamps must be timezone-aware.")

    lead_deadline = current_time + timedelta(minutes=settings.generation_lead_minutes)
    db = SessionLocal()
    work: list[tuple[UUID, UUID, UUID]] = []
    try:
        slots = db.execute(
            select(ExamSlot.id, ExamSlot.exam_id).where(
                ExamSlot.starts_at > current_time,
                ExamSlot.starts_at <= lead_deadline,
                ExamSlot.ends_at > current_time,
            )
        ).all()
        for slot_id, exam_id in slots:
            student_ids = db.scalars(
                select(SlotStudent.student_id).where(SlotStudent.slot_id == slot_id)
            ).all()
            for student_id in student_ids:
                if not _student_has_generation_record(db, slot_id, student_id):
                    work.append((slot_id, exam_id, student_id))
    except Exception as exc:  # noqa: BLE001 - keep scheduled discovery isolated.
        logger.error("Generation discovery failed (type=%s)", type(exc).__name__)
        return 0
    finally:
        db.close()

    for slot_id, exam_id, student_id in work:
        try:
            generation_service.generate_for_student(slot_id, student_id)
        except Exception as exc:  # noqa: BLE001 - one failed student must not stop the batch.
            logger.error(
                "Scheduled generation failed for slot=%s exam=%s student=%s (type=%s)",
                slot_id,
                exam_id,
                student_id,
                type(exc).__name__,
            )
    return len(work)


def run_attempt_auto_submit(now: datetime | None = None) -> int:
    """Finalize expired attempts without invoking Phase 12 grading."""
    try:
        return autosubmit_expired_attempts(now)
    except Exception as exc:  # noqa: BLE001 - scheduler jobs must not terminate the runner.
        logger.error(
            "Attempt auto-submit discovery failed (type=%s)", type(exc).__name__
        )
        return 0
