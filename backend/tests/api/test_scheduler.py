from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.models import (
    Assignment,
    Exam,
    ExamQuestion,
    ExamSlot,
    Profile,
    SlotStudent,
    Submission,
)
from app.db.session import get_db
from app.main import app
from app.scheduler.jobs import run_generation_discovery
from app.scheduler.scheduler import get_scheduler, shutdown_scheduler, start_scheduler
from app.services import generation_service


def _users(db):
    users = {
        user.email: user
        for user in db.scalars(
            select(Profile).where(
                Profile.email.in_(["teacher1@example.com", "student1@example.com", "student2@example.com"])
            )
        )
    }
    assert len(users) == 3
    return users["teacher1@example.com"], users["student1@example.com"], users["student2@example.com"]


def _slot(db, teacher, students, starts_at, ends_at):
    marker = uuid4().hex
    assignment = Assignment(teacher_id=teacher.id, title=f"Assignment {marker}", language="python")
    db.add(assignment)
    db.flush()
    exam = Exam(
        teacher_id=teacher.id,
        assignment_id=assignment.id,
        title=f"Exam {marker}",
        duration_minutes=30,
        num_questions=2,
    )
    db.add(exam)
    db.flush()
    slot = ExamSlot(exam_id=exam.id, starts_at=starts_at, ends_at=ends_at)
    db.add(slot)
    db.flush()
    db.add_all(SlotStudent(slot_id=slot.id, student_id=student.id) for student in students)
    db.commit()
    return assignment, exam, slot


def _submission(db, assignment, student):
    submission = Submission(
        assignment_id=assignment.id,
        student_id=student.id,
        filename="solution.py",
        code="print(42)",
        code_hash=uuid4().hex,
        code_facts={},
    )
    db.add(submission)
    db.commit()
    return submission


def _question(db, exam, slot, student, submission):
    db.add(
        ExamQuestion(
            exam_id=exam.id,
            slot_id=slot.id,
            student_id=student.id,
            submission_id=submission.id,
            order_idx=1,
            type="short_answer",
            prompt="Prompt",
            line_refs=[],
            answer_format="text",
            options=None,
            answer_key=None,
            rubric=None,
            max_score=Decimal(1),
            status="approved",
            question_hash=uuid4().hex,
        )
    )
    db.commit()


def _cleanup(db, records):
    slot_ids = [slot.id for _, _, slot in records]
    assignment_ids = [assignment.id for assignment, _, _ in records]
    exam_ids = [exam.id for _, exam, _ in records]
    db.execute(delete(ExamQuestion).where(ExamQuestion.slot_id.in_(slot_ids)))
    db.execute(delete(SlotStudent).where(SlotStudent.slot_id.in_(slot_ids)))
    db.execute(delete(ExamSlot).where(ExamSlot.id.in_(slot_ids)))
    db.execute(delete(Submission).where(Submission.assignment_id.in_(assignment_ids)))
    db.execute(delete(Exam).where(Exam.id.in_(exam_ids)))
    db.execute(delete(Assignment).where(Assignment.id.in_(assignment_ids)))
    db.commit()


def test_scheduler_discovers_only_due_missing_students(monkeypatch):
    db = next(get_db())
    records = []
    try:
        teacher, student1, student2 = _users(db)
        now = datetime.now(timezone.utc)
        eligible = _slot(
            db, teacher, [student1, student2], now + timedelta(minutes=10), now + timedelta(minutes=40)
        )
        before_lead = _slot(
            db, teacher, [student1], now + timedelta(hours=1), now + timedelta(hours=2)
        )
        past = _slot(
            db, teacher, [student1], now - timedelta(minutes=40), now - timedelta(minutes=10)
        )
        records.extend([eligible, before_lead, past])
        submission = _submission(db, eligible[0], student1)
        _question(db, eligible[1], eligible[2], student1, submission)
        calls = []

        def fake_generate(slot_id, student_id):
            calls.append((slot_id, student_id))

        monkeypatch.setattr(generation_service, "generate_for_student", fake_generate)
        assert run_generation_discovery(now) == 1
        assert calls == [(eligible[2].id, student2.id)]

        student2_submission = _submission(db, eligible[0], student2)
        _question(db, eligible[1], eligible[2], student2, student2_submission)
        assert run_generation_discovery(now) == 0
        assert calls == [(eligible[2].id, student2.id)]
    finally:
        _cleanup(db, records)
        db.close()


def test_scheduler_isolates_student_slot_failures_and_missing_submissions(monkeypatch):
    db = next(get_db())
    records = []
    try:
        teacher, student1, student2 = _users(db)
        now = datetime.now(timezone.utc)
        failing = _slot(
            db, teacher, [student1], now + timedelta(minutes=5), now + timedelta(minutes=35)
        )
        succeeding = _slot(
            db, teacher, [student2], now + timedelta(minutes=5), now + timedelta(minutes=35)
        )
        missing_submission = _slot(
            db, teacher, [student1], now + timedelta(minutes=5), now + timedelta(minutes=35)
        )
        records.extend([failing, succeeding, missing_submission])
        calls = []

        def fake_generate(slot_id, student_id):
            calls.append((slot_id, student_id))
            if slot_id == failing[2].id:
                raise RuntimeError("simulated task failure")

        monkeypatch.setattr(generation_service, "generate_for_student", fake_generate)
        assert run_generation_discovery(now) == 3
        assert (succeeding[2].id, student2.id) in calls
        assert (missing_submission[2].id, student1.id) in calls
    finally:
        _cleanup(db, records)
        db.close()


def test_scheduler_missing_submission_reuses_phase9_safe_skip(caplog):
    db = next(get_db())
    records = []
    try:
        teacher, student1, _ = _users(db)
        now = datetime.now(timezone.utc)
        record = _slot(
            db,
            teacher,
            [student1],
            now + timedelta(minutes=5),
            now + timedelta(minutes=35),
        )
        records.append(record)
        assert run_generation_discovery(now) == 1
        assert db.scalar(select(ExamQuestion.id).where(ExamQuestion.slot_id == record[2].id)) is None
        assert "no valid assignment submission" in caplog.text
    finally:
        _cleanup(db, records)
        db.close()


def test_scheduler_lifecycle_and_application_health():
    shutdown_scheduler()
    scheduler = start_scheduler()
    assert scheduler.running
    assert get_scheduler() is scheduler
    shutdown_scheduler()
    assert not scheduler.running

    with TestClient(app) as client:
        assert get_scheduler().running
        assert client.get("/health").json() == {"status": "ok", "service": "codeviva-api"}
    shutdown_scheduler()
