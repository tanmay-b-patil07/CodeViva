"""Phase 11 runtime ownership, timing, idempotency, and public-filter tests."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.security import AUTH_COOKIE_NAME, create_access_token
from app.db.models import (
    Answer,
    Assignment,
    AttemptResult,
    Exam,
    ExamAttempt,
    ExamQuestion,
    ExamSlot,
    Profile,
    SlotStudent,
    Submission,
)
from app.db.session import get_db
from app.main import app
from app.scheduler.jobs import run_attempt_auto_submit


def _users(db):
    users = {
        user.email: user
        for user in db.scalars(
            select(Profile).where(
                Profile.email.in_(
                    [
                        "teacher1@example.com",
                        "student1@example.com",
                        "student2@example.com",
                    ]
                )
            )
        )
    }
    return (
        users["teacher1@example.com"],
        users["student1@example.com"],
        users["student2@example.com"],
    )


def _auth(user):
    client = TestClient(app)
    client.cookies.set(AUTH_COOKIE_NAME, create_access_token(user.id, user.role))
    return client


def _runtime(db, teacher, students, *, starts, ends, duration=30, questions=1):
    assignment = Assignment(
        teacher_id=teacher.id, title=f"runtime-{uuid4().hex}", language="python"
    )
    db.add(assignment)
    db.flush()
    exam = Exam(
        teacher_id=teacher.id,
        assignment_id=assignment.id,
        title="Runtime exam",
        duration_minutes=duration,
        num_questions=questions,
    )
    db.add(exam)
    db.flush()
    slot = ExamSlot(exam_id=exam.id, starts_at=starts, ends_at=ends)
    db.add(slot)
    db.flush()
    for student in students:
        submission = Submission(
            assignment_id=assignment.id,
            student_id=student.id,
            filename="x.py",
            code="x=1",
            code_hash=uuid4().hex,
            code_facts={},
        )
        db.add(submission)
        db.flush()
        db.add(
            SlotStudent(
                slot_id=slot.id, student_id=student.id, submission_id=submission.id
            )
        )
        for index in range(questions):
            db.add(
                ExamQuestion(
                    exam_id=exam.id,
                    slot_id=slot.id,
                    student_id=student.id,
                    submission_id=submission.id,
                    order_idx=index + 1,
                    type="short",
                    prompt="Private source prompt",
                    line_refs=[],
                    answer_format="text",
                    options=None,
                    answer_key={"secret": "key"},
                    rubric={"secret": "rubric"},
                    max_score=Decimal(1),
                    status="approved",
                    question_hash=uuid4().hex,
                )
            )
    db.commit()
    return assignment, exam, slot


def _cleanup(db, assignment):
    slot_ids = db.scalars(
        select(ExamSlot.id).join(Exam).where(Exam.assignment_id == assignment.id)
    ).all()
    attempt_ids = db.scalars(
        select(ExamAttempt.id).where(ExamAttempt.slot_id.in_(slot_ids))
    ).all()
    db.execute(delete(AttemptResult).where(AttemptResult.attempt_id.in_(attempt_ids)))
    db.execute(delete(Answer).where(Answer.attempt_id.in_(attempt_ids)))
    db.execute(delete(ExamAttempt).where(ExamAttempt.id.in_(attempt_ids)))
    db.execute(delete(ExamQuestion).where(ExamQuestion.slot_id.in_(slot_ids)))
    db.execute(delete(SlotStudent).where(SlotStudent.slot_id.in_(slot_ids)))
    db.execute(delete(ExamSlot).where(ExamSlot.id.in_(slot_ids)))
    db.execute(delete(Submission).where(Submission.assignment_id == assignment.id))
    db.execute(delete(Exam).where(Exam.assignment_id == assignment.id))
    db.execute(delete(Assignment).where(Assignment.id == assignment.id))
    db.commit()


def test_runtime_listing_start_questions_and_public_filter():
    db = next(get_db())
    assignment = None
    try:
        teacher, student1, student2 = _users(db)
        now = datetime.now(timezone.utc)
        assignment, _, slot = _runtime(
            db,
            teacher,
            [student1, student2],
            starts=now - timedelta(minutes=1),
            ends=now + timedelta(minutes=20),
        )
        client = _auth(student1)
        listed = client.get("/api/student/slots")
        assert listed.status_code == 200
        assert all(
            field not in listed.text
            for field in (
                "answer_key", "rubric", "grading_error", "evidence",
                "confidence", "model", "code_facts",
            )
        )
        own = next(item for item in listed.json() if item["slot_id"] == str(slot.id))
        assert own["questions_ready"] and own["has_submission"]
        started = client.post(f"/api/student/slots/{slot.id}/start")
        assert started.status_code == 200
        resumed = client.post(f"/api/student/slots/{slot.id}/start")
        assert resumed.json()["attempt_id"] == started.json()["attempt_id"]
        assert resumed.json()["deadline_at"] == started.json()["deadline_at"]
        questions = client.get(
            f"/api/student/attempts/{started.json()['attempt_id']}/questions"
        )
        assert questions.status_code == 200
        assert all(
            field not in questions.text
            for field in (
                "answer_key", "rubric", "grading_error", "evidence",
                "confidence", "model", "code_facts",
            )
        )
        assert (
            _auth(student2)
            .get(f"/api/student/attempts/{started.json()['attempt_id']}/questions")
            .status_code
            == 404
        )
        assert _auth(teacher).get("/api/student/slots").status_code == 403
        assert TestClient(app).get("/api/student/slots").status_code == 401
    finally:
        if assignment:
            _cleanup(db, assignment)
        db.close()


def test_runtime_deadline_autosave_submit_and_auto_submit():
    db = next(get_db())
    assignment = None
    try:
        teacher, student1, student2 = _users(db)
        now = datetime.now(timezone.utc)
        assignment, _, slot = _runtime(
            db,
            teacher,
            [student1, student2],
            starts=now - timedelta(minutes=1),
            ends=now + timedelta(minutes=3),
            duration=60,
        )
        client = _auth(student1)
        started = client.post(f"/api/student/slots/{slot.id}/start").json()
        assert datetime.fromisoformat(started["deadline_at"]) <= slot.ends_at
        question = db.scalar(
            select(ExamQuestion).where(
                ExamQuestion.slot_id == slot.id, ExamQuestion.student_id == student1.id
            )
        )
        saved = client.put(
            f"/api/student/attempts/{started['attempt_id']}/answers/{question.id}",
            json={"answer_text": "first"},
        )
        assert saved.status_code == 200
        client.put(
            f"/api/student/attempts/{started['attempt_id']}/answers/{question.id}",
            json={"answer_text": "updated"},
        )
        assert (
            db.scalar(
                select(Answer.answer_text).where(
                    Answer.attempt_id == started["attempt_id"],
                    Answer.question_id == question.id,
                )
            )
            == "updated"
        )
        submitted = client.post(f"/api/student/attempts/{started['attempt_id']}/submit")
        assert submitted.status_code == 200 and not submitted.json()["auto_submitted"]
        assert (
            client.post(f"/api/student/attempts/{started['attempt_id']}/submit").json()
            == submitted.json()
        )
        assert db.get(AttemptResult, started["attempt_id"]).status == "pending"

        attempt2 = ExamAttempt(
            slot_id=slot.id,
            student_id=student2.id,
            started_at=now - timedelta(hours=1),
            deadline_at=now - timedelta(seconds=1),
        )
        db.add(attempt2)
        db.commit()
        assert run_attempt_auto_submit(now) == 1
        db.refresh(attempt2)
        assert attempt2.auto_submitted and attempt2.submitted_at is not None
        assert db.get(AttemptResult, attempt2.id).status == "pending"
    finally:
        if assignment:
            _cleanup(db, assignment)
        db.close()


def test_runtime_rejects_other_slot_question_and_closed_writes():
    db = next(get_db())
    assignment = None
    other_assignment = None
    try:
        teacher, student1, _ = _users(db)
        now = datetime.now(timezone.utc)
        assignment, _, slot = _runtime(
            db,
            teacher,
            [student1],
            starts=now - timedelta(minutes=1),
            ends=now + timedelta(minutes=10),
        )
        other_assignment, _, other_slot = _runtime(
            db,
            teacher,
            [student1],
            starts=now - timedelta(minutes=1),
            ends=now + timedelta(minutes=10),
        )
        client = _auth(student1)
        attempt_id = client.post(f"/api/student/slots/{slot.id}/start").json()[
            "attempt_id"
        ]
        other_question = db.scalar(
            select(ExamQuestion).where(ExamQuestion.slot_id == other_slot.id)
        )
        assert (
            client.put(
                f"/api/student/attempts/{attempt_id}/answers/{other_question.id}",
                json={"answer_text": "no"},
            ).status_code
            == 404
        )
        attempt = db.get(ExamAttempt, attempt_id)
        attempt.deadline_at = now - timedelta(minutes=2)
        db.commit()
        question = db.scalar(
            select(ExamQuestion).where(ExamQuestion.slot_id == slot.id)
        )
        assert (
            client.put(
                f"/api/student/attempts/{attempt_id}/answers/{question.id}",
                json={"answer_text": "late"},
            ).status_code
            == 409
        )
    finally:
        if other_assignment:
            _cleanup(db, other_assignment)
        if assignment:
            _cleanup(db, assignment)
        db.close()
