from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.authorization import (
    get_owned_assignment_or_404,
    get_owned_exam_or_404,
    get_owned_exam_slot_or_404,
    get_owned_group_or_404,
    get_student_attempt_or_404,
    get_student_practice_session_or_404,
    get_student_submission_or_404,
)
from app.db.models import (
    Assignment,
    Exam,
    ExamAttempt,
    ExamSlot,
    Group,
    PracticeSession,
    Profile,
    Submission,
)
from app.db.session import get_db


def get_test_users(db):
    teacher1 = db.scalar(
        select(Profile).where(Profile.email == "teacher1@example.com")
    )
    teacher2 = db.scalar(
        select(Profile).where(Profile.email == "teacher2@example.com")
    )
    student1 = db.scalar(
        select(Profile).where(Profile.email == "student1@example.com")
    )
    student2 = db.scalar(
        select(Profile).where(Profile.email == "student2@example.com")
    )

    assert teacher1 is not None
    assert teacher2 is not None
    assert student1 is not None
    assert student2 is not None

    return teacher1, teacher2, student1, student2


def test_ownership_helpers():
    db = next(get_db())

    try:
        teacher1, teacher2, student1, student2 = get_test_users(db)

        # ---------------------------------------------------------------
        # Groups
        # ---------------------------------------------------------------

        group1 = Group(
            name="Teacher 1 Group",
            teacher_id=teacher1.id,
        )

        group2 = Group(
            name="Teacher 2 Group",
            teacher_id=teacher2.id,
        )

        db.add_all([group1, group2])
        db.flush()

        assert (
            get_owned_group_or_404(
                db,
                group1.id,
                teacher1.id,
            ).id
            == group1.id
        )

        with pytest.raises(HTTPException) as exc:
            get_owned_group_or_404(
                db,
                group2.id,
                teacher1.id,
            )

        assert exc.value.status_code == 404

        # ---------------------------------------------------------------
        # Assignments
        # ---------------------------------------------------------------

        assignment1 = Assignment(
            teacher_id=teacher1.id,
            title="Teacher 1 Assignment",
            description="Ownership test",
            language="python",
        )

        assignment2 = Assignment(
            teacher_id=teacher2.id,
            title="Teacher 2 Assignment",
            description="Ownership test",
            language="python",
        )

        db.add_all([assignment1, assignment2])
        db.flush()

        assert (
            get_owned_assignment_or_404(
                db,
                assignment1.id,
                teacher1.id,
            ).id
            == assignment1.id
        )

        with pytest.raises(HTTPException) as exc:
            get_owned_assignment_or_404(
                db,
                assignment2.id,
                teacher1.id,
            )

        assert exc.value.status_code == 404

        # ---------------------------------------------------------------
        # Submissions
        # ---------------------------------------------------------------

        submission1 = Submission(
            assignment_id=assignment1.id,
            student_id=student1.id,
            filename="main.py",
            code="print('student 1')",
            code_hash="test-hash-1",
            code_facts={},
        )

        submission2 = Submission(
            assignment_id=assignment2.id,
            student_id=student2.id,
            filename="main.py",
            code="print('student 2')",
            code_hash="test-hash-2",
            code_facts={},
        )

        db.add_all([submission1, submission2])
        db.flush()

        assert (
            get_student_submission_or_404(
                db,
                submission1.id,
                student1.id,
            ).id
            == submission1.id
        )

        with pytest.raises(HTTPException) as exc:
            get_student_submission_or_404(
                db,
                submission2.id,
                student1.id,
            )

        assert exc.value.status_code == 404

        # ---------------------------------------------------------------
        # Practice sessions
        # ---------------------------------------------------------------

        practice1 = PracticeSession(
            student_id=student1.id,
            submission_id=submission1.id,
            status="ready",
        )

        practice2 = PracticeSession(
            student_id=student2.id,
            submission_id=submission2.id,
            status="ready",
        )

        db.add_all([practice1, practice2])
        db.flush()

        assert (
            get_student_practice_session_or_404(
                db,
                practice1.id,
                student1.id,
            ).id
            == practice1.id
        )

        with pytest.raises(HTTPException) as exc:
            get_student_practice_session_or_404(
                db,
                practice2.id,
                student1.id,
            )

        assert exc.value.status_code == 404

        # ---------------------------------------------------------------
        # Exams
        # ---------------------------------------------------------------

        exam1 = Exam(
            teacher_id=teacher1.id,
            assignment_id=assignment1.id,
            title="Teacher 1 Exam",
            duration_minutes=30,
            num_questions=5,
        )

        exam2 = Exam(
            teacher_id=teacher2.id,
            assignment_id=assignment2.id,
            title="Teacher 2 Exam",
            duration_minutes=30,
            num_questions=5,
        )

        db.add_all([exam1, exam2])
        db.flush()

        assert (
            get_owned_exam_or_404(
                db,
                exam1.id,
                teacher1.id,
            ).id
            == exam1.id
        )

        with pytest.raises(HTTPException) as exc:
            get_owned_exam_or_404(
                db,
                exam2.id,
                teacher1.id,
            )

        assert exc.value.status_code == 404

        # ---------------------------------------------------------------
        # Exam slots
        # ---------------------------------------------------------------

        now = datetime.now(timezone.utc)

        slot1 = ExamSlot(
            exam_id=exam1.id,
            group_id=group1.id,
            starts_at=now,
            ends_at=now + timedelta(minutes=30),
        )

        slot2 = ExamSlot(
            exam_id=exam2.id,
            group_id=group2.id,
            starts_at=now,
            ends_at=now + timedelta(minutes=30),
        )

        db.add_all([slot1, slot2])
        db.flush()

        assert (
            get_owned_exam_slot_or_404(
                db,
                slot1.id,
                teacher1.id,
            ).id
            == slot1.id
        )

        with pytest.raises(HTTPException) as exc:
            get_owned_exam_slot_or_404(
                db,
                slot2.id,
                teacher1.id,
            )

        assert exc.value.status_code == 404

        # ---------------------------------------------------------------
        # Exam attempts
        # ---------------------------------------------------------------

        attempt1 = ExamAttempt(
            slot_id=slot1.id,
            student_id=student1.id,
            started_at=now,
            deadline_at=now + timedelta(minutes=30),
        )

        attempt2 = ExamAttempt(
            slot_id=slot2.id,
            student_id=student2.id,
            started_at=now,
            deadline_at=now + timedelta(minutes=30),
        )

        db.add_all([attempt1, attempt2])
        db.flush()

        assert (
            get_student_attempt_or_404(
                db,
                attempt1.id,
                student1.id,
            ).id
            == attempt1.id
        )

        with pytest.raises(HTTPException) as exc:
            get_student_attempt_or_404(
                db,
                attempt2.id,
                student1.id,
            )

        assert exc.value.status_code == 404

    finally:
        db.rollback()
        db.close()