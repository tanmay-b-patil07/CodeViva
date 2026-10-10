"""Phase 12 grading gateway, persistence, and student-safe result tests."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.errors import AppError
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
from app.schemas.grading import GradingResult, QuestionGrade
from app.services import grading_gateway
from app.services.grading_service import grade_submitted_attempt


def _auth(user):
    client = TestClient(app)
    client.cookies.set(AUTH_COOKIE_NAME, create_access_token(user.id, user.role))
    return client


def _records(db):
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


def _attempt(db, teacher, student, *, submitted=True, auto=False):
    now = datetime.now(timezone.utc)
    assignment = Assignment(
        teacher_id=teacher.id, title=f"grading-{uuid4().hex}", language="python"
    )
    db.add(assignment)
    db.flush()
    exam = Exam(
        teacher_id=teacher.id,
        assignment_id=assignment.id,
        title="Grading",
        duration_minutes=30,
        num_questions=1,
    )
    db.add(exam)
    db.flush()
    slot = ExamSlot(
        exam_id=exam.id,
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
    )
    db.add(slot)
    db.flush()
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
        SlotStudent(slot_id=slot.id, student_id=student.id, submission_id=submission.id)
    )
    question = ExamQuestion(
        exam_id=exam.id,
        slot_id=slot.id,
        student_id=student.id,
        submission_id=submission.id,
        order_idx=1,
        type="short",
        prompt="Explain x",
        line_refs=[],
        answer_format="text",
        options=None,
        answer_key={"secret": "key"},
        rubric={"secret": "rubric"},
        max_score=Decimal(5),
        status="approved",
        question_hash=uuid4().hex,
    )
    db.add(question)
    db.flush()
    attempt = ExamAttempt(
        slot_id=slot.id,
        student_id=student.id,
        started_at=now,
        deadline_at=now + timedelta(minutes=30),
        submitted_at=now if submitted else None,
        auto_submitted=auto,
    )
    db.add(attempt)
    db.flush()
    answer = Answer(
        attempt_id=attempt.id,
        question_id=question.id,
        answer_text="Because x is one.",
        saved_at=now,
    )
    db.add(answer)
    db.commit()
    return assignment, attempt, question, answer


def _cleanup(db, assignment):
    slots = db.scalars(
        select(ExamSlot.id).join(Exam).where(Exam.assignment_id == assignment.id)
    ).all()
    attempts = db.scalars(
        select(ExamAttempt.id).where(ExamAttempt.slot_id.in_(slots))
    ).all()
    answer_ids = db.scalars(
        select(Answer.id).where(Answer.attempt_id.in_(attempts))
    ).all()
    db.execute(delete(Score).where(Score.answer_id.in_(answer_ids)))
    db.execute(delete(AttemptResult).where(AttemptResult.attempt_id.in_(attempts)))
    db.execute(delete(Answer).where(Answer.attempt_id.in_(attempts)))
    db.execute(delete(ExamAttempt).where(ExamAttempt.id.in_(attempts)))
    db.execute(delete(ExamQuestion).where(ExamQuestion.slot_id.in_(slots)))
    db.execute(delete(SlotStudent).where(SlotStudent.slot_id.in_(slots)))
    db.execute(delete(ExamSlot).where(ExamSlot.id.in_(slots)))
    db.execute(delete(Submission).where(Submission.assignment_id == assignment.id))
    db.execute(delete(Exam).where(Exam.assignment_id == assignment.id))
    db.execute(delete(Assignment).where(Assignment.id == assignment.id))
    db.commit()


def _successful_gateway(calls):
    async def fake(payload):
        calls.append(payload)
        return GradingResult(
            attempt_id=payload.attempt_id,
            total_score=Decimal(4),
            max_score=Decimal(5),
            question_grades=[
                QuestionGrade(
                    question_id=payload.questions[0].id,
                    awarded_score=Decimal(4),
                    max_score=Decimal(5),
                    feedback="Good",
                    evidence="Answer addresses x",
                    confidence=Decimal("0.9"),
                )
            ],
        )

    return fake


def test_gateway_contract_persistence_and_idempotency(monkeypatch):
    db = next(get_db())
    assignment = None
    try:
        teacher, student, _ = _records(db)
        assignment, attempt, _question, answer = _attempt(db, teacher, student)
        calls = []
        monkeypatch.setattr(
            grading_gateway, "grade_attempt", _successful_gateway(calls)
        )
        first = grade_submitted_attempt(db, attempt.id)
        second = grade_submitted_attempt(db, attempt.id)
        assert first.status == second.status == "graded"
        assert first.total_score == Decimal(4) and first.max_score == Decimal(5)
        assert len(calls) == 1
        assert calls[0].questions[0].answer.answer_text == answer.answer_text
        assert calls[0].questions[0].answer_key == {"secret": "key"}
        score = db.scalar(select(Score).where(Score.answer_id == answer.id))
        assert score.score == Decimal(4) and score.feedback == "Good"
        assert (
            db.scalar(
                select(AttemptResult).where(AttemptResult.attempt_id == attempt.id)
            ).attempt_id
            == attempt.id
        )
    finally:
        if assignment:
            _cleanup(db, assignment)
        db.close()


def test_rejects_unsubmitted_and_records_gateway_failure(monkeypatch):
    db = next(get_db())
    assignment = None
    failed_assignment = None
    try:
        teacher, student, _ = _records(db)
        assignment, attempt, _, _ = _attempt(db, teacher, student, submitted=False)
        with pytest.raises(AppError, match="submitted"):
            grade_submitted_attempt(db, attempt.id)
        assert db.get(AttemptResult, attempt.id) is None

        failed_assignment, failed_attempt, _, _ = _attempt(db, teacher, student)

        async def broken(_payload):
            raise RuntimeError("evaluator unavailable")

        monkeypatch.setattr(grading_gateway, "grade_attempt", broken)
        result = grade_submitted_attempt(db, failed_attempt.id)
        assert result.status == "failed"
        assert (
            result.total_score is None
            and result.grading_error == "evaluator unavailable"
        )
        assert (
            db.scalar(
                select(Score.id)
                .join(Answer)
                .where(Answer.attempt_id == failed_attempt.id)
            )
            is None
        )
        failed_response = _auth(student).get(
            f"/api/student/attempts/{failed_attempt.id}/result"
        )
        assert failed_response.status_code == 200
        assert failed_response.json()["grading_status"] == "failed"
        assert failed_response.json()["questions"] == []
        assert all(
            field not in failed_response.text
            for field in (
                "grading_error", "answer_key", "rubric", "evidence",
                "confidence", "model", "code_facts",
            )
        )
    finally:
        if failed_assignment:
            _cleanup(db, failed_assignment)
        if assignment:
            _cleanup(db, assignment)
        db.close()


def test_auto_submitted_and_student_result_security(monkeypatch):
    db = next(get_db())
    assignment = None
    try:
        teacher, student, other_student = _records(db)
        assignment, attempt, _, _ = _attempt(db, teacher, student, auto=True)
        calls = []
        monkeypatch.setattr(
            grading_gateway, "grade_attempt", _successful_gateway(calls)
        )
        assert grade_submitted_attempt(db, attempt.id).status == "graded"
        path = f"/api/student/attempts/{attempt.id}/result"
        response = _auth(student).get(path)
        assert response.status_code == 200
        body = response.json()
        assert body["auto_submitted"] and body["grading_status"] == "graded"
        assert body["total_score"] == "4"
        assert (
            "answer_key" not in response.text
            and "rubric" not in response.text
            and "evidence" not in response.text
        )
        assert all(
            field not in response.text
            for field in ("grading_error", "confidence", "model", "code_facts")
        )
        assert _auth(other_student).get(path).status_code == 404
        assert _auth(teacher).get(path).status_code == 403
        assert TestClient(app).get(path).status_code == 401
    finally:
        if assignment:
            _cleanup(db, assignment)
        db.close()


def test_pending_student_result_has_no_invented_score():
    db = next(get_db())
    assignment = None
    try:
        teacher, student, _ = _records(db)
        assignment, attempt, _, _ = _attempt(db, teacher, student)
        response = _auth(student).get(f"/api/student/attempts/{attempt.id}/result")
        assert response.status_code == 200
        assert response.json()["grading_status"] == "pending"
        assert response.json()["total_score"] is None
    finally:
        if assignment:
            _cleanup(db, assignment)
        db.close()
