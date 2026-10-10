from unittest.mock import Mock

from app.db.models import Profile
from app.db.session import get_db
from app.services.submissions import (
    calculate_code_hash,
    create_submission,
    find_cached_facts,
)
from sqlalchemy import select


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

        assert find_cached_facts(db, code_hash, "python") == fake_facts
        assert find_cached_facts(db, code_hash, "cpp") == cpp_facts

    finally:
        for submission in created:
            db.delete(submission)

        db.commit()
        db.close()