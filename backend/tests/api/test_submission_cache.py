from unittest.mock import Mock
from uuid import uuid4

from app.core.deps import get_current_user, get_database
from app.db.models import Assignment, Profile, Submission
from app.db.session import get_db
from app.main import app
from app.routers import submissions as submissions_router
from app.services.submissions import (
    calculate_code_hash,
    create_submission,
    find_cached_facts,
)
from fastapi.testclient import TestClient
from sqlalchemy import delete, select


def test_same_hash_reuses_cached_facts():
    db = next(get_db())

    created = []

    try:
        student = db.scalar(
            select(Profile).where(
                Profile.email == "student1@example.com"
            )
        )

        assert student is not None

        code = """print("CodeViva")
"""

        code_hash = calculate_code_hash(code)

        fake_facts = {
            "language": "python",
            "functions": [],
            "imports": [],
            "classes": [],
        }

        analysis = Mock(return_value=fake_facts)

        # First analysis.
        facts = analysis(code)

        first = create_submission(
            db,
            student_id=student.id,
            filename="cache_test.py",
            code=code,
            assignment_id=None,
            code_facts=facts,
            code_hash=code_hash,
        )

        created.append(first)

        assert analysis.call_count == 1

        # Second submission with identical code.
        cached = find_cached_facts(
            db,
            code_hash,
            student_id=student.id,
            assignment_id=None,
        )

        assert cached == fake_facts

        # Because facts were cached, analysis must NOT run again.
        assert analysis.call_count == 1

        cpp_facts = {
            "language": "cpp",
            "functions": [],
            "imports": [],
            "classes": [],
        }
        second = create_submission(
            db,
            student_id=student.id,
            filename="cache_test.cpp",
            code=code,
            assignment_id=None,
            code_facts=cpp_facts,
            code_hash=code_hash,
        )
        created.append(second)

        assert find_cached_facts(
            db,
            code_hash,
            student_id=student.id,
            assignment_id=None,
            language="python",
        ) == fake_facts
        assert find_cached_facts(
            db,
            code_hash,
            student_id=student.id,
            assignment_id=None,
            language="cpp",
        ) == cpp_facts

    finally:
        for submission in created:
            db.delete(submission)

        db.commit()
        db.close()


def test_submission_api_cache_is_scoped_to_student_and_assignment(monkeypatch):
    db = next(get_db())
    teacher_id = uuid4()
    student_a_id = uuid4()
    student_b_id = uuid4()
    assignment_a_id = uuid4()
    assignment_b_id = uuid4()
    teacher = Profile(
        id=teacher_id,
        email=f"cache-teacher-{teacher_id}@example.test",
        password_hash="synthetic-not-a-real-hash",
        full_name="Cache Test Teacher",
        role="teacher",
    )
    student_a = Profile(
        id=student_a_id,
        email=f"cache-student-a-{student_a_id}@example.test",
        password_hash="synthetic-not-a-real-hash",
        full_name="Cache Student A",
        role="student",
    )
    student_b = Profile(
        id=student_b_id,
        email=f"cache-student-b-{student_b_id}@example.test",
        password_hash="synthetic-not-a-real-hash",
        full_name="Cache Student B",
        role="student",
    )
    assignments = [
        Assignment(
            id=assignment_a_id,
            teacher_id=teacher_id,
            title="Cache Context A",
            language="python",
        ),
        Assignment(
            id=assignment_b_id,
            teacher_id=teacher_id,
            title="Cache Context B",
            language="python",
        ),
    ]
    db.add_all([teacher, student_a, student_b])
    db.flush()
    db.add_all(assignments)
    db.commit()

    active_student = [student_a]
    previous_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = lambda: active_student[0]

    def override_database():
        yield db

    app.dependency_overrides[get_database] = override_database
    analysis_calls = []

    def fake_extract_facts(code):
        facts = {"owner_marker": f"analysis-{len(analysis_calls) + 1}"}
        analysis_calls.append(code)
        return facts

    monkeypatch.setattr(submissions_router, "extract_facts", fake_extract_facts)
    client = TestClient(app)
    source = b"print('same normalized source')\n"

    def submit(assignment_id):
        data = {"assignment_id": str(assignment_id)} if assignment_id else {}
        return client.post(
            "/api/student/submissions",
            files={"file": ("cache.py", source, "text/x-python")},
            data=data,
        )

    try:
        first_a = submit(assignment_a_id)
        assert first_a.status_code == 201
        assert first_a.json()["code_facts"] == {"owner_marker": "analysis-1"}

        repeated_a = submit(assignment_a_id)
        assert repeated_a.status_code == 201
        assert repeated_a.json()["code_facts"] == {"owner_marker": "analysis-1"}
        assert len(analysis_calls) == 1

        different_assignment = submit(assignment_b_id)
        assert different_assignment.status_code == 201
        assert different_assignment.json()["code_facts"] == {
            "owner_marker": "analysis-2"
        }
        assert len(analysis_calls) == 2

        active_student[0] = student_b
        other_student = submit(assignment_a_id)
        assert other_student.status_code == 201
        assert other_student.json()["code_facts"] == {"owner_marker": "analysis-3"}

        other_student_repeat = submit(assignment_a_id)
        assert other_student_repeat.status_code == 201
        assert other_student_repeat.json()["code_facts"] == {
            "owner_marker": "analysis-3"
        }
        assert len(analysis_calls) == 3
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        db.execute(
            delete(Submission).where(
                Submission.student_id.in_([student_a_id, student_b_id])
            )
        )
        db.execute(
            delete(Assignment).where(
                Assignment.id.in_([assignment_a_id, assignment_b_id])
            )
        )
        db.execute(
            delete(Profile).where(Profile.id.in_([teacher_id, student_a_id, student_b_id]))
        )
        db.commit()
        db.close()
