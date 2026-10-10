from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.security import AUTH_COOKIE_NAME, create_access_token
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
from app.services import exam_generation_gateway


def _headers(user: Profile) -> dict[str, str]:
    return {
        "Cookie": f"{AUTH_COOKIE_NAME}={create_access_token(user.id, user.role)}"
    }


def _users(db):
    users = {
        user.email: user
        for user in db.scalars(
            select(Profile).where(
                Profile.email.in_(
                    ["teacher1@example.com", "teacher2@example.com", "student1@example.com", "student2@example.com"]
                )
            )
        )
    }
    assert len(users) == 4
    return tuple(users[email] for email in sorted(users))


def _question(question_hash: str) -> dict:
    return {
        "type": "short_answer",
        "prompt": "What does this code print?",
        "line_refs": [1],
        "answer_format": "text",
        "options": None,
        "answer_key": {"value": "42"},
        "rubric": {"correct": 1},
        "max_score": 1,
        "question_hash": question_hash,
    }


def _create_slot(db, teacher, students, *, auto_approve=True):
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
        auto_approve=auto_approve,
    )
    now = datetime.now(timezone.utc)
    db.add(exam)
    db.flush()
    slot = ExamSlot(
        exam_id=exam.id,
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, minutes=30),
    )
    db.add(slot)
    db.flush()
    db.add_all(SlotStudent(slot_id=slot.id, student_id=student.id) for student in students)
    db.commit()
    return assignment, exam, slot


def _cleanup(db, assignment, exam, slot):
    db.execute(delete(ExamQuestion).where(ExamQuestion.slot_id == slot.id))
    db.execute(delete(SlotStudent).where(SlotStudent.slot_id == slot.id))
    db.execute(delete(ExamSlot).where(ExamSlot.id == slot.id))
    db.execute(delete(Submission).where(Submission.assignment_id == assignment.id))
    db.execute(delete(Exam).where(Exam.id == exam.id))
    db.execute(delete(Assignment).where(Assignment.id == assignment.id))
    db.commit()


def test_generation_uses_linked_and_latest_submissions(monkeypatch):
    db = next(get_db())
    assignment = exam = slot = None
    try:
        student1, student2, teacher1, teacher2 = _users(db)
        assignment, exam, slot = _create_slot(db, teacher1, [student1, student2])
        old = Submission(
            assignment_id=assignment.id,
            student_id=student1.id,
            filename="old.py",
            code="linked-code",
            code_hash="linked-hash",
            code_facts={"student": 1},
        )
        latest = Submission(
            assignment_id=assignment.id,
            student_id=student2.id,
            filename="latest.py",
            code="latest-code",
            code_hash="latest-hash",
            code_facts={"student": 2},
            created_at=datetime.now(timezone.utc),
        )
        db.add_all([old, latest])
        db.flush()
        linked = db.get(SlotStudent, (slot.id, student1.id))
        assert linked is not None
        linked.submission_id = old.id
        db.commit()

        calls = []

        async def fake_generate(code, facts, n, avoid_hashes):
            calls.append((code, facts, n, avoid_hashes))
            return [_question(f"question-{code}")]

        monkeypatch.setattr(exam_generation_gateway, "generate_exam_questions", fake_generate)
        response = TestClient(app).post(
            f"/api/teacher/slots/{slot.id}/generate", headers=_headers(teacher1)
        )
        assert response.status_code == 202, response.text
        assert response.json() == {"status": "generation_started", "queued_students": 2}
        assert {(code, n) for code, _, n, _ in calls} == {
            ("linked-code", 2),
            ("latest-code", 2),
        }

        db.expire_all()
        linked_after = db.get(SlotStudent, (slot.id, student1.id))
        fallback_after = db.get(SlotStudent, (slot.id, student2.id))
        assert linked_after.submission_id == old.id
        assert fallback_after.submission_id == latest.id
        questions = db.scalars(
            select(ExamQuestion).where(ExamQuestion.slot_id == slot.id)
        ).all()
        assert {(q.student_id, q.submission_id) for q in questions} == {
            (student1.id, old.id),
            (student2.id, latest.id),
        }
        assert all(question.status == "approved" for question in questions)
        assert all(question.answer_key == {"value": "42"} for question in questions)
        assert all(question.rubric == {"correct": 1} for question in questions)

        assert TestClient(app).post(
            f"/api/teacher/slots/{slot.id}/generate", headers=_headers(teacher1)
        ).status_code == 409
        assert TestClient(app).post(
            f"/api/teacher/slots/{slot.id}/generate", headers=_headers(teacher2)
        ).status_code == 404
        assert TestClient(app).post(
            f"/api/teacher/slots/{slot.id}/generate", headers=_headers(student1)
        ).status_code == 403
        assert TestClient(app).post(f"/api/teacher/slots/{slot.id}/generate").status_code == 401
    finally:
        if assignment is not None:
            _cleanup(db, assignment, exam, slot)
        db.close()


def test_generation_failure_and_missing_submission_are_isolated(monkeypatch, caplog):
    db = next(get_db())
    assignment = exam = slot = None
    try:
        student1, student2, teacher1, _ = _users(db)
        assignment, exam, slot = _create_slot(db, teacher1, [student1, student2])
        submission = Submission(
            assignment_id=assignment.id,
            student_id=student2.id,
            filename="works.py",
            code="works",
            code_hash="works-hash",
            code_facts={"works": True},
        )
        db.add(submission)
        db.commit()

        async def fake_generate(code, facts, n, avoid_hashes):
            return [_question("works-question")]

        monkeypatch.setattr(exam_generation_gateway, "generate_exam_questions", fake_generate)
        response = TestClient(app).post(
            f"/api/teacher/slots/{slot.id}/generate", headers=_headers(teacher1)
        )
        assert response.status_code == 202, response.text
        questions = db.scalars(
            select(ExamQuestion).where(ExamQuestion.slot_id == slot.id)
        ).all()
        assert len(questions) == 1
        assert questions[0].student_id == student2.id
        assert "no valid assignment submission" in caplog.text
    finally:
        if assignment is not None:
            _cleanup(db, assignment, exam, slot)
        db.close()


def test_generation_failure_marks_failed_and_non_auto_approve_stays_draft(monkeypatch):
    db = next(get_db())
    assignment = exam = slot = None
    try:
        student1, student2, teacher1, _ = _users(db)
        assignment, exam, slot = _create_slot(
            db, teacher1, [student1, student2], auto_approve=False
        )
        db.add_all(
            [
                Submission(
                    assignment_id=assignment.id,
                    student_id=student1.id,
                    filename="bad.py",
                    code="bad",
                    code_hash="bad-hash",
                    code_facts={},
                ),
                Submission(
                    assignment_id=assignment.id,
                    student_id=student2.id,
                    filename="good.py",
                    code="good",
                    code_hash="good-hash",
                    code_facts={},
                ),
            ]
        )
        db.commit()

        async def fake_generate(code, facts, n, avoid_hashes):
            if code == "bad":
                raise RuntimeError("simulated generator failure")
            return [_question("good-question")]

        monkeypatch.setattr(exam_generation_gateway, "generate_exam_questions", fake_generate)
        response = TestClient(app).post(
            f"/api/teacher/slots/{slot.id}/generate", headers=_headers(teacher1)
        )
        assert response.status_code == 202, response.text
        questions = db.scalars(
            select(ExamQuestion).where(ExamQuestion.slot_id == slot.id)
        ).all()
        statuses = {question.student_id: question.status for question in questions}
        assert statuses == {student1.id: "failed", student2.id: "draft"}
    finally:
        if assignment is not None:
            _cleanup(db, assignment, exam, slot)
        db.close()
