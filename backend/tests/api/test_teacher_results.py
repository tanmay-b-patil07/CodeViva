"""Phase 13 teacher result ownership and aggregate API tests."""

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
    Score,
    SlotStudent,
    Submission,
)
from app.db.session import get_db
from app.main import app


def _auth(user):
    client = TestClient(app)
    client.cookies.set(AUTH_COOKIE_NAME, create_access_token(user.id, user.role))
    return client


def _profile(db, role, email):
    profile = Profile(email=email, password_hash="test", full_name=email, role=role)
    db.add(profile)
    db.flush()
    return profile


def _seed_attempt(db, exam, slot, student, *, result_status, score=None, auto=False):
    now = datetime.now(timezone.utc)
    submission = Submission(assignment_id=exam.assignment_id, student_id=student.id, filename="a.py", code="x=1", code_hash=uuid4().hex, code_facts={})
    db.add(submission)
    db.flush()
    db.add(SlotStudent(slot_id=slot.id, student_id=student.id, submission_id=submission.id))
    question = ExamQuestion(exam_id=exam.id, slot_id=slot.id, student_id=student.id, submission_id=submission.id, order_idx=1, type="short", prompt="Private prompt", line_refs=[], answer_format="text", options=None, answer_key={"hidden": "key"}, rubric={"hidden": "rubric"}, max_score=Decimal(10), status="approved", question_hash=uuid4().hex)
    db.add(question)
    db.flush()
    attempt = ExamAttempt(slot_id=slot.id, student_id=student.id, started_at=now, deadline_at=now + timedelta(minutes=30), submitted_at=now, auto_submitted=auto)
    db.add(attempt)
    db.flush()
    answer = Answer(attempt_id=attempt.id, question_id=question.id, answer_text="answer", saved_at=now)
    db.add(answer)
    db.flush()
    result = AttemptResult(attempt_id=attempt.id, status=result_status)
    if result_status == "graded":
        result.total_score = score
        result.max_score = Decimal(10)
        result.percentage = score * Decimal(10)
        result.graded_at = now
        db.add(Score(answer_id=answer.id, score=score, max_score=Decimal(10), evidence="private evidence", confidence=Decimal("0.8"), needs_review=False, feedback="Helpful feedback"))
    elif result_status == "failed":
        result.grading_error = "private gateway failure"
    db.add(result)
    return attempt, question


def _fixture(db):
    marker = uuid4().hex
    teacher_a = _profile(db, "teacher", f"phase13-a-{marker}@example.com")
    teacher_b = _profile(db, "teacher", f"phase13-b-{marker}@example.com")
    students = [_profile(db, "student", f"phase13-s{i}-{marker}@example.com") for i in range(1, 4)]
    assignments = []
    exams = []
    slots = []
    for teacher, title in ((teacher_a, "A"), (teacher_b, "B")):
        assignment = Assignment(teacher_id=teacher.id, title=f"{title}-{marker}", language="python")
        db.add(assignment)
        db.flush()
        exam = Exam(teacher_id=teacher.id, assignment_id=assignment.id, title=title, duration_minutes=30, num_questions=1)
        db.add(exam)
        db.flush()
        now = datetime.now(timezone.utc)
        slot = ExamSlot(exam_id=exam.id, starts_at=now - timedelta(hours=1), ends_at=now + timedelta(hours=1))
        db.add(slot)
        db.flush()
        assignments.append(assignment)
        exams.append(exam)
        slots.append(slot)
    own_attempts = [
        _seed_attempt(db, exams[0], slots[0], students[0], result_status="graded", score=Decimal(8)),
        _seed_attempt(db, exams[0], slots[0], students[1], result_status="pending", auto=True),
        _seed_attempt(db, exams[0], slots[0], students[2], result_status="failed"),
    ]
    other_attempt, _ = _seed_attempt(db, exams[1], slots[1], students[0], result_status="graded", score=Decimal(6))
    db.commit()
    return teacher_a, teacher_b, students, assignments, exams, slots, own_attempts, other_attempt


def _cleanup(db, assignments, students, slots):
    slot_ids = [slot.id for slot in slots]
    assignment_ids = [assignment.id for assignment in assignments]
    attempts = db.scalars(select(ExamAttempt.id).where(ExamAttempt.slot_id.in_(slot_ids))).all()
    answers = db.scalars(select(Answer.id).where(Answer.attempt_id.in_(attempts))).all()
    db.execute(delete(Score).where(Score.answer_id.in_(answers)))
    db.execute(delete(AttemptResult).where(AttemptResult.attempt_id.in_(attempts)))
    db.execute(delete(Answer).where(Answer.attempt_id.in_(attempts)))
    db.execute(delete(ExamAttempt).where(ExamAttempt.id.in_(attempts)))
    db.execute(delete(ExamQuestion).where(ExamQuestion.slot_id.in_(slot_ids)))
    db.execute(delete(SlotStudent).where(SlotStudent.slot_id.in_(slot_ids)))
    db.execute(delete(ExamSlot).where(ExamSlot.id.in_(slot_ids)))
    db.execute(delete(Submission).where(Submission.assignment_id.in_(assignment_ids)))
    db.execute(delete(Exam).where(Exam.assignment_id.in_(assignment_ids)))
    db.execute(delete(Assignment).where(Assignment.id.in_(assignment_ids)))
    db.execute(delete(Profile).where(Profile.id.in_([student.id for student in students])))
    db.commit()


def test_teacher_results_listing_individual_and_analytics():
    db = next(get_db())
    fixture = None
    try:
        fixture = _fixture(db)
        teacher_a, _teacher_b, students, _assignments, exams, slots, attempts, _other = fixture
        client = _auth(teacher_a)
        listing = client.get(f"/api/teacher/results?exam_id={exams[0].id}")
        assert listing.status_code == 200
        assert len(listing.json()["items"]) == 3
        assert client.get(f"/api/teacher/results?slot_id={slots[0].id}&status=graded&limit=1").json()["items"][0]["total_score"] == "8"
        assert client.get(f"/api/teacher/results?student_id={students[1].id}").json()["items"][0]["grading_status"] == "pending"
        individual = client.get(f"/api/teacher/results/{attempts[0][0].id}")
        assert individual.status_code == 200
        body = individual.json()
        assert body["questions"][0]["awarded_score"] == "8"
        assert all(
            field not in individual.text
            for field in (
                "answer_key", "rubric", "evidence", "grading_error",
                "confidence", "model", "code_facts",
            )
        )
        summary = client.get(f"/api/teacher/exams/{exams[0].id}/analytics").json()
        assert summary["assigned_students"] == 3 and summary["started_attempts"] == 3 and summary["submitted_attempts"] == 3
        assert summary["auto_submitted_attempts"] == 1 and summary["normal_submitted_attempts"] == 2
        assert summary["pending_results"] == 1 and summary["graded_results"] == 1 and summary["failed_results"] == 1
        assert Decimal(summary["average_score"]) == Decimal(8)
        assert Decimal(summary["highest_score"]) == Decimal(8)
        assert Decimal(summary["lowest_score"]) == Decimal(8)
        assert Decimal(summary["submission_rate"]) == Decimal(100)
        assert client.get(f"/api/teacher/slots/{slots[0].id}/analytics").json()["graded_results"] == 1
        questions = client.get(f"/api/teacher/exams/{exams[0].id}/question-analytics").json()["questions"]
        graded_question = next(item for item in questions if item["question_id"] == str(attempts[0][1].id))
        assert graded_question["answered_count"] == 1 and graded_question["graded_count"] == 1
        assert Decimal(graded_question["average_awarded_score"]) == Decimal(8)
    finally:
        if fixture:
            teacher_a, teacher_b, students, assignments, _exams, slots, _attempts, _other = fixture
            _cleanup(db, assignments, students, slots)
            db.execute(delete(Profile).where(Profile.id.in_([teacher_a.id, teacher_b.id])))
            db.commit()
        db.close()


def test_teacher_result_security_and_pending_failed_states():
    db = next(get_db())
    fixture = None
    try:
        fixture = _fixture(db)
        teacher_a, teacher_b, students, _assignments, exams, slots, attempts, other_attempt = fixture
        own_client = _auth(teacher_a)
        other_client = _auth(teacher_b)
        student_client = _auth(students[0])
        assert TestClient(app).get("/api/teacher/results").status_code == 401
        assert student_client.get("/api/teacher/results").status_code == 403
        assert other_client.get(f"/api/teacher/results/{attempts[0][0].id}").status_code == 404
        assert other_client.get(f"/api/teacher/exams/{exams[0].id}/analytics").status_code == 404
        assert other_client.get(f"/api/teacher/slots/{slots[0].id}/analytics").status_code == 404
        assert own_client.get(f"/api/teacher/results/{other_attempt.id}").status_code == 404
        pending = own_client.get(f"/api/teacher/results/{attempts[1][0].id}").json()
        failed = own_client.get(f"/api/teacher/results/{attempts[2][0].id}").json()
        assert pending["grading_status"] == "pending" and pending["total_score"] is None
        assert failed["grading_status"] == "failed" and failed["total_score"] is None
        assert own_client.get("/api/teacher/results?status=unknown").status_code == 422
    finally:
        if fixture:
            teacher_a, teacher_b, students, assignments, _exams, slots, _attempts, _other = fixture
            _cleanup(db, assignments, students, slots)
            db.execute(delete(Profile).where(Profile.id.in_([teacher_a.id, teacher_b.id])))
            db.commit()
        db.close()
